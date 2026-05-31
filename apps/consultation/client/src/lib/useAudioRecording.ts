import { useCallback, useRef, useState, type MutableRefObject } from "react";
import { pickSupportedRecordingMimeType } from "./mediaCapture";
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

	const cleanupRecorderResources = useCallback(() => {
		mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
		mediaStreamRef.current = null;
		mediaRecorderRef.current = null;
		audioChunksRef.current = [];
		if (elapsedTimerRef.current !== null) {
			clearInterval(elapsedTimerRef.current);
			elapsedTimerRef.current = null;
		}
	}, []);

	const startRecording = useCallback(async () => {
		if (typeof window === "undefined" || typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
			const feedback = getUnsupportedMediaFeedback("microphone");
			setMicrophoneFeedback(feedback);
			onError?.(feedback.detail);
			return;
		}

		if (typeof MediaRecorder === "undefined") {
			const feedback = getUnsupportedMediaFeedback("microphone");
			setMicrophoneFeedback(feedback);
			onError?.(feedback.detail);
			return;
		}

		try {
			setMicrophoneFeedback({
				title: "正在检测麦克风",
				detail: "浏览器正在申请麦克风权限并初始化录音设备。",
				tone: "pending",
			});
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			const mimeType = pickSupportedRecordingMimeType();
			const recorder = mimeType
				? new MediaRecorder(stream, { mimeType })
				: new MediaRecorder(stream);
			const startedAt = new Date();

			audioChunksRef.current = [];
			mediaStreamRef.current = stream;
			mediaRecorderRef.current = recorder;
			recordingStartedAtRef.current = startedAt;
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
				if (event.data.size > 0) {
					audioChunksRef.current.push(event.data);
				}
			};

			recorder.onerror = () => {
				cleanupRecorderResources();
				recordingStartedAtRef.current = null;
				setIsRecording(false);
				setRecordingElapsedMs(0);
				const feedback: MediaDeviceFeedback = {
					title: "麦克风采集失败",
					detail: "录音过程中出现错误，请检查设备占用或浏览器权限后重试。",
					tone: "error",
				};
				setMicrophoneFeedback(feedback);
				onError?.("浏览器录音过程中出现错误，请重试。");
			};

			recorder.onstop = () => {
				if (elapsedTimerRef.current !== null) {
					clearInterval(elapsedTimerRef.current);
					elapsedTimerRef.current = null;
				}
				if (isUnmountingRef?.current) {
					cleanupRecorderResources();
					recordingStartedAtRef.current = null;
					return;
				}

				const completedAt = new Date();
				const responseStartedAt = recordingStartedAtRef.current || completedAt;
				const blob = new Blob(audioChunksRef.current, {
					type: recorder.mimeType || "audio/webm",
				});
				recordingStartedAtRef.current = null;
				setIsRecording(false);
				setRecordingElapsedMs(0);

				onRecordingComplete({
					blob,
					mimeType: recorder.mimeType || "audio/webm",
					startedAt: responseStartedAt,
					completedAt,
				});
			};

			recorder.start();
		} catch (caught) {
			const feedback = describeMediaAccessError("microphone", caught);
			cleanupRecorderResources();
			recordingStartedAtRef.current = null;
			setIsRecording(false);
			setRecordingElapsedMs(0);
			setMicrophoneFeedback(feedback);
			onError?.(feedback.detail);
		}
	}, [cleanupRecorderResources, onRecordingComplete, onError, isUnmountingRef]);

	const stopRecording = useCallback(() => {
		const recorder = mediaRecorderRef.current;
		if (!recorder || recorder.state !== "recording") {
			return;
		}
		// onstop fires and triggers onRecordingComplete
		recorder.stop();
	}, []);

	const cancelRecording = useCallback(() => {
		const recorder = mediaRecorderRef.current;
		cleanupRecorderResources();
		recordingStartedAtRef.current = null;
		setIsRecording(false);
		setRecordingElapsedMs(0);
		if (recorder && recorder.state === "recording") {
			recorder.stop();
		}
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
