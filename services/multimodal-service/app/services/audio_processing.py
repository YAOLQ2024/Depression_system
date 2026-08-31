from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

from app.config import get_settings

SUPPORTED_MIME_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".mp4",
}


class AudioProcessingError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


def ensure_processing_directory(audio_turn_id: str) -> Path:
    base_dir = get_settings()["upload_processing_dir"]
    target_dir = base_dir / audio_turn_id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def cleanup_processing_directory(audio_turn_id: str) -> None:
    target_dir = get_settings()["upload_processing_dir"] / audio_turn_id
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)


def normalize_mime_type(raw_mime_type: str | None) -> str:
    if not raw_mime_type:
        return ""
    return raw_mime_type.split(";", 1)[0].strip().lower()


def resolve_mime_type(
    declared_mime_type: str,
    upload_content_type: str | None,
) -> str:
    normalized = normalize_mime_type(declared_mime_type)
    if normalized not in SUPPORTED_MIME_TYPES:
        raise AudioProcessingError(
            "unsupported audio mime type",
            error_code="UNSUPPORTED_MIME_TYPE",
            status_code=415,
        )

    if upload_content_type:
        normalized_upload_type = normalize_mime_type(upload_content_type)
        if (
            normalized_upload_type
            and normalized_upload_type in SUPPORTED_MIME_TYPES
            and normalized_upload_type != normalized
        ):
            raise AudioProcessingError(
                "declared mime type does not match uploaded file",
                error_code="MIME_TYPE_MISMATCH",
                status_code=400,
            )

    return normalized


def resolve_audio_suffix(mime_type: str, source_filename: str | None) -> str:
    if source_filename:
        suffix = Path(source_filename).suffix.lower()
        if suffix:
            return suffix
    return SUPPORTED_MIME_TYPES[mime_type]


def write_source_audio_file(
    processing_dir: Path,
    suffix: str,
    file_bytes: bytes,
) -> Path:
    source_path = processing_dir / f"source{suffix}"
    source_path.write_bytes(file_bytes)
    return source_path


def convert_to_wav(source_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise AudioProcessingError(
            "failed to normalize uploaded audio",
            error_code="AUDIO_CONVERSION_FAILED",
            status_code=400,
        )


def trim_leading_silence(source_wav_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_wav_path),
        "-af",
        "silenceremove=start_periods=1:start_silence=0:start_threshold=-30dB",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise AudioProcessingError(
            "failed to trim leading silence from wav",
            error_code="AUDIO_CONVERSION_FAILED",
            status_code=400,
        )


def get_wav_duration_ms(wav_path: Path) -> int:
    with wave.open(str(wav_path), "rb") as wav_file:
        frames = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            raise AudioProcessingError(
                "invalid wav sample rate",
                error_code="INVALID_AUDIO_FILE",
                status_code=400,
            )
        return int((frames / frame_rate) * 1000)
