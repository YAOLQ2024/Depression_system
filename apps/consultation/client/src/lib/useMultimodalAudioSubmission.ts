import { useCallback } from "react";

import { logAudioDebug } from "./audioDebug";
import type { MultimodalAudioTurnRecord } from "../services/api/multimodal.api";
import { normalizeAudioMimeType } from "./mediaCapture";
import type { RecordingCompletedPayload } from "./useAudioRecording";
import { useTranscriptPolling } from "./useTranscriptPolling";

type SubmitRecordedAudioArgs<TContext> = {
	payload: RecordingCompletedPayload;
	context: TContext;
	ensureSession: () => Promise<string>;
	emptyRecordingMessage: string;
	emptyTranscriptMessage: string;
	uploadAudioTurn: (args: {
		sessionId: string;
		blob: Blob;
		resolvedMimeType: string;
		durationMs: number;
		startedAtIso: string;
		completedAtIso: string;
		context: TContext;
	}) => Promise<MultimodalAudioTurnRecord>;
};

export type SubmittedRecordedAudio = {
	sessionId: string;
	uploadedAudioTurn: MultimodalAudioTurnRecord;
	transcriptReadyAudioTurn: MultimodalAudioTurnRecord;
	transcriptText: string;
	resolvedMimeType: string;
	durationMs: number;
	startedAtIso: string;
	completedAtIso: string;
};

export function useMultimodalAudioSubmission() {
	const { pollForTranscript } = useTranscriptPolling();

	const submitRecordedAudio = useCallback(
		async <TContext>({
			payload,
			context,
			ensureSession,
			emptyRecordingMessage,
			emptyTranscriptMessage,
			uploadAudioTurn,
		}: SubmitRecordedAudioArgs<TContext>): Promise<SubmittedRecordedAudio> => {
			const { blob, mimeType, startedAt, completedAt } = payload;
			logAudioDebug("submission.begin", {
				blobSize: blob.size,
				blobType: blob.type || "",
				mimeType,
				startedAt: startedAt.toISOString(),
				completedAt: completedAt.toISOString(),
			});
			if (blob.size <= 0) {
				logAudioDebug("submission.empty_blob");
				throw new Error(emptyRecordingMessage);
			}

			const sessionId = await ensureSession();
			const resolvedMimeType = normalizeAudioMimeType(mimeType || blob.type || "audio/webm");
			const durationMs = completedAt.getTime() - startedAt.getTime();
			const startedAtIso = startedAt.toISOString();
			const completedAtIso = completedAt.toISOString();

			logAudioDebug("submission.upload.request", {
				sessionId,
				resolvedMimeType,
				durationMs,
			});
			const uploadedAudioTurn = await uploadAudioTurn({
				sessionId,
				blob,
				resolvedMimeType,
				durationMs,
				startedAtIso,
				completedAtIso,
				context,
			});
			logAudioDebug("submission.upload.response", {
				sessionId,
				audioTurnId: uploadedAudioTurn.audio_turn_id,
				processingStatus: uploadedAudioTurn.processing_status,
				hasTranscript: Boolean(uploadedAudioTurn.transcript_text?.trim()),
			});
			const transcriptReadyAudioTurn =
				(uploadedAudioTurn.transcript_text?.trim() || "").length > 0
					? uploadedAudioTurn
					: await pollForTranscript(sessionId, uploadedAudioTurn.audio_turn_id);
			const transcriptText = transcriptReadyAudioTurn.transcript_text?.trim() || "";
			logAudioDebug("submission.transcript.resolved", {
				audioTurnId: transcriptReadyAudioTurn.audio_turn_id,
				processingStatus: transcriptReadyAudioTurn.processing_status,
				transcriptLength: transcriptText.length,
			});
			if (!transcriptText) {
				logAudioDebug("submission.transcript.empty", {
					audioTurnId: transcriptReadyAudioTurn.audio_turn_id,
				});
				throw new Error(emptyTranscriptMessage);
			}

			return {
				sessionId,
				uploadedAudioTurn,
				transcriptReadyAudioTurn,
				transcriptText,
				resolvedMimeType,
				durationMs,
				startedAtIso,
				completedAtIso,
			};
		},
		[pollForTranscript],
	);

	return { submitRecordedAudio };
}
