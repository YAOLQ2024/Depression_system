import { useEffect, useRef, useState } from "react";
import {
	describeMediaAccessError,
	getInitialMediaFeedback,
	getReadyMediaFeedback,
	getUnsupportedMediaFeedback,
	type MediaDeviceFeedback,
} from "./mediaDeviceFeedback";

type UseCameraOptions = {
	enabled?: boolean;
};

type UseCameraResult = {
	cameraReady: boolean;
	cameraStream: MediaStream | null;
	cameraError: string;
	cameraFeedback: MediaDeviceFeedback;
};

export function useCamera({ enabled = true }: UseCameraOptions = {}): UseCameraResult {
	const cameraStreamRef = useRef<MediaStream | null>(null);

	const [cameraReady, setCameraReady] = useState(false);
	const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
	const [cameraError, setCameraError] = useState("");
	const [cameraFeedback, setCameraFeedback] = useState<MediaDeviceFeedback>(() =>
		getInitialMediaFeedback("camera"),
	);

	useEffect(() => {
		if (!enabled) {
			return;
		}

		if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
			const unsupported = getUnsupportedMediaFeedback("camera");
			setCameraError(unsupported.detail);
			setCameraFeedback(unsupported);
			return;
		}

		let cancelled = false;

		async function setupCamera() {
			try {
				setCameraFeedback(getInitialMediaFeedback("camera"));
				const stream = await navigator.mediaDevices.getUserMedia({
					video: {
						facingMode: "user",
						width: { ideal: 960 },
						height: { ideal: 720 },
					},
				});
				if (cancelled) {
					stream.getTracks().forEach((track) => track.stop());
					return;
				}
				cameraStreamRef.current = stream;
				setCameraStream(stream);
				setCameraReady(true);
				setCameraError("");
				setCameraFeedback(
					getReadyMediaFeedback("camera", "画面采集中，可持续上传表情与姿态帧。"),
				);
			} catch (caught) {
				if (!cancelled) {
					const feedback = describeMediaAccessError("camera", caught);
					setCameraReady(false);
					setCameraStream(null);
					setCameraError(feedback.detail);
					setCameraFeedback(feedback);
				}
			}
		}

		void setupCamera();

		return () => {
			cancelled = true;
			cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
			cameraStreamRef.current = null;
			setCameraStream(null);
			setCameraReady(false);
		};
	}, [enabled]);

	return { cameraReady, cameraStream, cameraError, cameraFeedback };
}
