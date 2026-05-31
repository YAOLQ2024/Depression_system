const RECORDING_MIME_CANDIDATES = [
	"audio/ogg;codecs=opus",
	"audio/ogg",
	"audio/webm;codecs=opus",
	"audio/webm",
	"audio/mp4",
];

export function pickSupportedRecordingMimeType() {
	if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
		return "";
	}

	return (
		RECORDING_MIME_CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || ""
	);
}

export async function captureVideoFrame(
	videoElement: HTMLVideoElement,
	mimeType = "image/jpeg",
): Promise<Blob | null> {
	if (!videoElement.videoWidth || !videoElement.videoHeight) {
		return null;
	}
	const canvas = document.createElement("canvas");
	canvas.width = videoElement.videoWidth;
	canvas.height = videoElement.videoHeight;
	const context = canvas.getContext("2d");
	if (!context) {
		return null;
	}
	context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
	return new Promise<Blob | null>((resolve) => {
		canvas.toBlob((blob) => resolve(blob), mimeType, 0.85);
	});
}

export function formatDuration(durationMs: number) {
	const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
	const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
	const seconds = String(totalSeconds % 60).padStart(2, "0");
	return `${minutes}:${seconds}`;
}

export function resolveRecordingExtension(mimeType: string) {
	if (mimeType.includes("mp4")) {
		return "mp4";
	}
	if (mimeType.includes("ogg")) {
		return "ogg";
	}
	return "webm";
}

export function normalizeAudioMimeType(mimeType: string) {
	return mimeType.split(";", 1)[0]?.trim().toLowerCase() || "audio/webm";
}

export function buildRecordingFilename(fileStem: string, mimeType: string) {
	return `${fileStem}.${resolveRecordingExtension(mimeType)}`;
}

export function sleep(ms: number) {
	return new Promise<void>((resolve) => {
		window.setTimeout(resolve, ms);
	});
}
