from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class AudioNormalizationError(Exception):
    pass


def normalize_audio_to_wav(
    *,
    file_bytes: bytes,
    source_suffix: str,
) -> bytes:
    suffix = source_suffix if source_suffix.startswith(".") else f".{source_suffix}"
    with tempfile.TemporaryDirectory(prefix="consultation-audio-") as temp_dir:
        temp_path = Path(temp_dir)
        source_path = temp_path / f"source{suffix}"
        output_path = temp_path / "normalized.wav"
        source_path.write_bytes(file_bytes)

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
        if completed.returncode != 0 or not output_path.exists():
            stderr = (completed.stderr or "").strip()
            raise AudioNormalizationError(
                stderr or "failed to normalize uploaded audio"
            )
        return output_path.read_bytes()
