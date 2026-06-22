import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { logAudioDebug } from "./audioDebug";
import { buildPreferredAudioConstraints, pickSupportedRecordingMimeType } from "./mediaCapture";
import {
	describeMediaAccessError,
	getActiveMicrophoneFeedback,
	getUnsupportedMediaFeedback,
	type MediaDeviceFeedback,
} from "./mediaDeviceFeedback";

export type RecordingCompletedPayload = {
	blob: Blob;
	mimeType: string;
	startedAt: Date;
	completedAt: Date;
};

type UseAudioRecordingOptions = {
	onRecordingComplete: (payload: RecordingCompletedPayload) => void;
	onError?: (message: string) => void;
	isUnmountingRef?: MutableRefObject<boolean>;
};

type UseAudioRecordingResult = {
	isRecording: boolean;
	recordingElapsedMs: number;
	microphoneFeedback: MediaDeviceFeedback;
	mediaRecorderRef: MutableRefObject<MediaRecorder | null>;
	mediaStreamRef: MutableRefObject<MediaStream | null>;
	audioChunksRef: MutableRefObject<Blob[]>;
	recordingStartedAtRef: MutableRefObject<Date | null>;
	startRecording: () => Promise<void>;
	stopRecording: () => void;
	cancelRecording: () => void;
	cleanupRecorderResources: () => void;
};

export function useAudioRecording({
	onRecordingComplete,
	onError,
	isUnmountingRef,
}: UseAudioRecordingOptions): UseAudioRecordingResult {
	const RECORDING_CHUNK_TIMESLICE_MS = 250;
	const STOP_EVENT_RECOVERY_TIMEOUT_MS = 1500;
	const FORCE_FINALIZE_TIMEOUT_MS = 240;

	const [isRecording, setIsRecording] = useState(false);
	const [recordingElapsedMs, setRecordingElapsedMs] = useState(0);
	const [microphoneFeedback, setMicrophoneFeedback] = useState<MediaDeviceFeedback>(() =>
		getInitialMicrophoneFeedback(),
	);

	const mediaRecorderRef = useRef<MediaRecorder | null>(null);
	const mediaStreamRef = useRef<MediaStream | null>(null);
	const audioChunksRef = useRef<Blob[]>([]);
	const recordingStartedAtRef = useRef<Date | null>(null);
	const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const stopRecoveryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const forceFinalizeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const pendingCompletionRef = useRef(false);
	const onRecordingCompleteRef = useRef(onRecordingComplete);
	const onErrorRef = useRef(onError);

	useEffect(() => {
		onRecordingCompleteRef.current = onRecordingComplete;
	}, [onRecordingComplete]);

	useEffect(() => {
		onErrorRef.current = onError;
	}, [onError]);

	const clearElapsedTimer = useCallback(() => {
		if (elapsedTimerRef.current !== null) {
			clearInterval(elapsedTimerRef.current);
			elapsedTimerRef.current = null;
		}
	}, []);

	const clearStopTimers = useCallback(() => {
		if (stopRecoveryTimerRef.current !== null) {
			clearTimeout(stopRecoveryTimerRef.current);
			stopRecoveryTimerRef.current = null;
		}
		if (forceFinalizeTimerRef.current !== null) {
			clearTimeout(forceFinalizeTimerRef.current);
			forceFinalizeTimerRef.current = null;
		}
	}, []);

	const resetRecordingUiState = useCallback(() => {
		recordingStartedAtRef.current = null;
		setIsRecording(false);
		setRecordingElapsedMs(0);
	}, []);

	const releaseMediaStream = useCallback(() => {
		mediaStreamRef.current?.getTracks().forEach((track) => {
			track.onended = null;
			track.stop();
		});
		mediaStreamRef.current = null;
	}, []);

	const cleanupRecorderResources = useCallback(() => {
		clearStopTimers();
		clearElapsedTimer();
		releaseMediaStream();
		mediaRecorderRef.current = null;
		audioChunksRef.current = [];
	}, [clearElapsedTimer, clearStopTimers, releaseMediaStream]);

	const finalizeRecording = useCallback(
		(recorder: MediaRecorder | null) => {
			if (!pendingCompletionRef.current) {
				logAudioDebug("recording.finalize.skipped", {
					reason: "pending_completion_false",
					recorderState: recorder?.state ?? null,
				});
				return;
			}

			pendingCompletionRef.current = false;
			clearStopTimers();
			clearElapsedTimer();

			const completedAt = new Date();
			const startedAt = recordingStartedAtRef.current || completedAt;
			const mimeType = recorder?.mimeType || "audio/webm";
			const audioChunks = [...audioChunksRef.current];
			const totalBytes = audioChunks.reduce((sum, chunk) => sum + chunk.size, 0);

			audioChunksRef.current = [];
			mediaRecorderRef.current = null;
			releaseMediaStream();
			resetRecordingUiState();

			logAudioDebug("recording.finalize", {
				recorderState: recorder?.state ?? null,
				chunkCount: audioChunks.length,
				totalBytes,
				mimeType,
				startedAt: startedAt.toISOString(),
				completedAt: completedAt.toISOString(),
				isUnmounting: Boolean(isUnmountingRef?.current),
			});

			if (isUnmountingRef?.current) {
				return;
			}

			void onRecordingCompleteRef.current({
				blob: new Blob(audioChunks, { type: mimeType }),
				mimeType,
				startedAt,
				completedAt,
			});
		},
		[
			clearElapsedTimer,
			clearStopTimers,
			isUnmountingRef,
			releaseMediaStream,
			resetRecordingUiState,
		],
	);

	const startRecording = useCallback(async () => {
		if (typeof window === "undefined" || typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
			const feedback = getUnsupportedMediaFeedback("microphone");
			setMicrophoneFeedback(feedback);
			logAudioDebug("recording.start.unavailable", { reason: "media_devices_unavailable" });
			onErrorRef.current?.(feedback.detail);
			return;
		}

		if (typeof MediaRecorder === "undefined") {
			const feedback = getUnsupportedMediaFeedback("microphone");
			setMicrophoneFeedback(feedback);
			logAudioDebug("recording.start.unavailable", { reason: "media_recorder_unavailable" });
			onErrorRef.current?.(feedback.detail);
			return;
		}

		try {
			pendingCompletionRef.current = false;
			cleanupRecorderResources();
			resetRecordingUiState();
			setMicrophoneFeedback({
				title: "正在检测麦克风",
				detail: "浏览器正在申请麦克风权限并初始化录音设备。",
				tone: "pending",
			});
			const stream = await navigator.mediaDevices.getUserMedia({
				audio: buildPreferredAudioConstraints(),
			});
			const mimeType = pickSupportedRecordingMimeType();
			const recorder = mimeType
				? new MediaRecorder(stream, { mimeType })
				: new MediaRecorder(stream);
			const startedAt = new Date();
			logAudioDebug("recording.start.ready", {
				mimeType: mimeType || recorder.mimeType || "",
				streamTracks: stream.getTracks().map((track) => ({
					kind: track.kind,
					label: track.label,
					readyState: track.readyState,
					settings: typeof track.getSettings === "function" ? track.getSettings() : null,
					constraints: typeof track.getConstraints === "function" ? track.getConstraints() : null,
				})),
			});

			audioChunksRef.current = [];
			mediaStreamRef.current = stream;
			mediaRecorderRef.current = recorder;
			recordingStartedAtRef.current = startedAt;
			pendingCompletionRef.current = true;
			setRecordingElapsedMs(0);
			setIsRecording(true);
			setMicrophoneFeedback(getActiveMicrophoneFeedback());

			elapsedTimerRef.current = setInterval(() => {
				const started = recordingStartedAtRef.current;
				if (started) {
					setRecordingElapsedMs(new Date().getTime() - started.getTime());
				}
			}, 100);

			recorder.ondataavailable = (event) => {
				logAudioDebug("recording.chunk", {
					size: event.data.size,
					type: event.data.type || "",
				});
				if (event.data.size > 0) {
					audioChunksRef.current.push(event.data);
				}
			};

			const handleTrackEnded = () => {
				const activeRecorder = mediaRecorderRef.current;
				logAudioDebug("recording.track_ended", {
					recorderState: activeRecorder?.state ?? null,
					pendingCompletion: pendingCompletionRef.current,
				});
				if (!activeRecorder || !pendingCompletionRef.current) {
					return;
				}
				if (activeRecorder.state === "recording") {
					try {
						activeRecorder.requestData();
					} catch {
						// Ignore recorder implementations that do not support flushing here.
					}
					try {
						activeRecorder.stop();
						return;
					} catch {
						// Fall through to the manual finalizer below.
					}
				}
				finalizeRecording(activeRecorder);
			};

			stream.getTracks().forEach((track) => {
				track.onended = handleTrackEnded;
			});

			recorder.onerror = () => {
				pendingCompletionRef.current = false;
				cleanupRecorderResources();
				resetRecordingUiState();
				logAudioDebug("recording.error", {
					recorderState: recorder.state,
				});
				const feedback: MediaDeviceFeedback = {
					title: "麦克风采集失败",
					detail: "录音过程中出现错误，请检查设备占用或浏览器权限后重试。",
					tone: "error",
				};
				setMicrophoneFeedback(feedback);
				onErrorRef.current?.("浏览器录音过程中出现错误，请重试。");
			};

			recorder.onstop = () => {
				logAudioDebug("recording.onstop", {
					recorderState: recorder.state,
				});
				finalizeRecording(recorder);
			};

			recorder.start(RECORDING_CHUNK_TIMESLICE_MS);
		} catch (caught) {
			pendingCompletionRef.current = false;
			const feedback = describeMediaAccessError("microphone", caught);
			cleanupRecorderResources();
			resetRecordingUiState();
			setMicrophoneFeedback(feedback);
			logAudioDebug("recording.start.failed", {
				error: caught instanceof Error ? caught.message : String(caught),
			});
			onErrorRef.current?.(feedback.detail);
		}
	}, [
		cleanupRecorderResources,
		finalizeRecording,
		resetRecordingUiState,
		RECORDING_CHUNK_TIMESLICE_MS,
	]);

	const stopRecording = useCallback(() => {
		const recorder = mediaRecorderRef.current;
		logAudioDebug("recording.stop.requested", {
			hasRecorder: Boolean(recorder),
			recorderState: recorder?.state ?? null,
			pendingCompletion: pendingCompletionRef.current,
			recordedChunkCount: audioChunksRef.current.length,
			recordedBytes: audioChunksRef.current.reduce((sum, chunk) => sum + chunk.size, 0),
		});
		if (!recorder) {
			pendingCompletionRef.current = false;
			cleanupRecorderResources();
			resetRecordingUiState();
			logAudioDebug("recording.stop.no_recorder");
			return;
		}
		if (recorder.state !== "recording") {
			logAudioDebug("recording.stop.non_recording_state", {
				recorderState: recorder.state,
			});
			finalizeRecording(recorder);
			return;
		}

		clearStopTimers();
		try {
			recorder.requestData();
		} catch {
			// Some browsers do not support flushing while stopping. Safe to ignore.
		}
		try {
			recorder.stop();
		} catch {
			logAudioDebug("recording.stop.stop_failed", {
				recorderState: recorder.state,
			});
			finalizeRecording(recorder);
			return;
		}

		stopRecoveryTimerRef.current = setTimeout(() => {
			logAudioDebug("recording.stop.recovery_timeout", {
				recorderState: recorder.state,
				pendingCompletion: pendingCompletionRef.current,
			});
			if (!pendingCompletionRef.current) {
				return;
			}

			try {
				recorder.requestData();
			} catch {
				// Ignore and continue with the forced shutdown path below.
			}

			releaseMediaStream();
			forceFinalizeTimerRef.current = setTimeout(() => {
				if (pendingCompletionRef.current) {
					logAudioDebug("recording.stop.force_finalize", {
						recorderState: recorder.state,
					});
					finalizeRecording(recorder);
				}
			}, FORCE_FINALIZE_TIMEOUT_MS);
		}, STOP_EVENT_RECOVERY_TIMEOUT_MS);
	}, [
		cleanupRecorderResources,
		clearStopTimers,
		finalizeRecording,
		releaseMediaStream,
		resetRecordingUiState,
	]);

	const cancelRecording = useCallback(() => {
		const recorder = mediaRecorderRef.current;
		logAudioDebug("recording.cancel", {
			hasRecorder: Boolean(recorder),
			recorderState: recorder?.state ?? null,
		});
		pendingCompletionRef.current = false;
		clearStopTimers();
		clearElapsedTimer();
		if (recorder && recorder.state === "recording") {
			try {
				recorder.stop();
			} catch {
				// Ignore shutdown errors during cancellation.
			}
		}
		cleanupRecorderResources();
		resetRecordingUiState();
	}, [cleanupRecorderResources, clearElapsedTimer, clearStopTimers, resetRecordingUiState]);

	useEffect(() => {
		return () => {
			pendingCompletionRef.current = false;
			cleanupRecorderResources();
			recordingStartedAtRef.current = null;
		};
	}, [cleanupRecorderResources]);

	function getInitialMicrophoneFeedback(): MediaDeviceFeedback {
		return { title: "麦克风未激活", detail: "", tone: "pending" };
	}

	return {
		isRecording,
		recordingElapsedMs,
		microphoneFeedback,
		mediaRecorderRef,
		mediaStreamRef,
		audioChunksRef,
		recordingStartedAtRef,
		startRecording,
		stopRecording,
		cancelRecording,
		cleanupRecorderResources,
	};
}
