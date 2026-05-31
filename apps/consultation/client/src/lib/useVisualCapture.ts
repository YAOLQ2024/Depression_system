import { useCallback, useEffect, useRef, type RefObject } from "react";

import { captureVideoFrame } from "./mediaCapture";

type VisualCaptureUploadPayload<TContext> = {
	blob: Blob;
	sampleIndex: number;
	startedAt: string;
	endedAt: string;
	context: TContext | undefined;
};

type UseVisualCaptureOptions<TContext = void> = {
	enabled: boolean;
	cameraStream: MediaStream | null;
	videoRef: RefObject<HTMLVideoElement | null>;
	uploadFn: (payload: VisualCaptureUploadPayload<TContext>) => Promise<void>;
	intervalMs?: number;
};

type UseVisualCaptureResult<TContext> = {
	captureNow: (context?: TContext) => Promise<boolean>;
	resetCaptureCount: () => void;
	getCaptureCount: () => number;
};

const VISUAL_CAPTURE_INTERVAL_MS = 1500;

export function useVisualCapture<TContext = void>({
	enabled,
	cameraStream,
	videoRef,
	uploadFn,
	intervalMs = VISUAL_CAPTURE_INTERVAL_MS,
}: UseVisualCaptureOptions<TContext>): UseVisualCaptureResult<TContext> {
	const frameIndexRef = useRef(0);
	const captureInFlightRef = useRef(false);
	const uploadFnRef = useRef(uploadFn);

	useEffect(() => {
		uploadFnRef.current = uploadFn;
	}, [uploadFn]);

	const captureNow = useCallback(
		async (context?: TContext) => {
			const video = videoRef.current;
			if (!video || captureInFlightRef.current) {
				return false;
			}
			if (typeof document !== "undefined" && document.visibilityState === "hidden") {
				return false;
			}
			if (!cameraStream || !cameraStream.active) {
				return false;
			}

			captureInFlightRef.current = true;
			const startedAt = new Date().toISOString();

			try {
				const blob = await captureVideoFrame(video);
				if (!blob) {
					return false;
				}

				frameIndexRef.current += 1;
				const sampleIndex = frameIndexRef.current;
				const endedAt = new Date().toISOString();

				await uploadFnRef.current({
					blob,
					sampleIndex,
					startedAt,
					endedAt,
					context,
				});
				return true;
			} finally {
				captureInFlightRef.current = false;
			}
		},
		[cameraStream, videoRef],
	);

	useEffect(() => {
		if (!enabled) {
			return;
		}

		const timer = setInterval(() => {
			void captureNow().catch(() => {
				// Best-effort — keep capturing even if one upload fails.
			});
		}, intervalMs);

		return () => clearInterval(timer);
	}, [captureNow, enabled, intervalMs]);

	const resetCaptureCount = useCallback(() => {
		frameIndexRef.current = 0;
	}, []);

	const getCaptureCount = useCallback(() => frameIndexRef.current, []);

	return { captureNow, resetCaptureCount, getCaptureCount };
}
