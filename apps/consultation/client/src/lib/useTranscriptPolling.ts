import { useState, useRef, useCallback } from "react";
import { sleep } from "./mediaCapture";
import { getMultimodalAudioTurn, type MultimodalAudioTurnRecord } from "../services/api/multimodal.api";

type UseTranscriptPollingOptions = {
	maxAttempts?: number;
	pollIntervalMs?: number;
};

type UseTranscriptPollingResult = {
	pollForTranscript: (sessionId: string, audioTurnId: string) => Promise<MultimodalAudioTurnRecord>;
	isPolling: boolean;
	error: string | null;
};

export function useTranscriptPolling({
	maxAttempts = 90,
	pollIntervalMs = 200,
}: UseTranscriptPollingOptions = {}): UseTranscriptPollingResult {
	const [isPolling, setIsPolling] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const abortRef = useRef(false);

	const pollForTranscript = useCallback(
		async (sessionId: string, audioTurnId: string) => {
			abortRef.current = false;
			setIsPolling(true);
			setError(null);

			try {
				for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
					if (abortRef.current) {
						throw new Error("Dolphin 语音转写已取消。");
					}

					const audioTurn = await getMultimodalAudioTurn(sessionId, audioTurnId);
					const transcriptText = audioTurn.transcript_text?.trim() || "";
					if (transcriptText) {
						return audioTurn;
					}
					if (audioTurn.processing_status === "failed") {
						throw new Error(
							audioTurn.error_message || "Dolphin 语音转写失败",
						);
					}
					await sleep(pollIntervalMs);
				}

				throw new Error("Dolphin 语音转写超时，请重试。");
			} catch (caught) {
				const message = caught instanceof Error ? caught.message : "转写轮询失败";
				setError(message);
				throw caught;
			} finally {
				setIsPolling(false);
			}
		},
		[maxAttempts, pollIntervalMs],
	);

	return { pollForTranscript, isPolling, error };
}
