from __future__ import annotations

from dataclasses import dataclass
import re
import threading
from pathlib import Path

from app.config import get_settings


_DOLPHIN_CONTROL_TOKEN_PATTERN = re.compile(
    r"(?:<(?:zh|cn|asr|notimestamp)>\s*)+",
    flags=re.IGNORECASE,
)


class DolphinAsrError(Exception):
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass(slots=True)
class DolphinTranscriptionResult:
    transcript_text: str
    transcript_confidence: float | None
    resolved_device: str


class DolphinAsrRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded_device: str | None = None
        self._model = None
        self._dolphin_module = None
        self._transcribe_function = None

    def validate_model_assets(self) -> None:
        model_dir = get_settings()["dolphin_model_dir"]
        if not model_dir.exists() or not model_dir.is_dir():
            raise DolphinAsrError(
                "dolphin model directory is missing",
                error_code="MODEL_NOT_READY",
            )

        asset_files = [
            candidate
            for candidate in model_dir.rglob("*")
            if candidate.is_file()
            and candidate.name.lower() not in {"readme.md", ".gitkeep"}
        ]
        if not asset_files:
            raise DolphinAsrError(
                "dolphin model assets are missing",
                error_code="MODEL_NOT_READY",
            )

    def _resolve_device(self) -> str:
        configured = get_settings()["asr_device"]
        if configured in {"cpu", "cuda"}:
            return configured

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            return "cpu"
        return "cpu"

    def resolve_device(self) -> str:
        return self._resolve_device()

    def _load_model_from_candidates(self, dolphin_module, model_name: str, device: str):
        model_dir = get_settings()["dolphin_model_dir"]
        parent_dir = model_dir.parent
        candidates = [
            lambda: dolphin_module.load_model(
                model_name,
                model_dir=str(model_dir),
                device=device,
            ),
            lambda: dolphin_module.load_model(
                model_name,
                model_dir=str(parent_dir),
                device=device,
            ),
            lambda: dolphin_module.load_model(model_name, str(model_dir), device),
            lambda: dolphin_module.load_model(model_name, str(parent_dir), device),
        ]
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                return candidate()
            except TypeError as exc:
                last_error = exc
                continue
        raise DolphinAsrError(
            f"unsupported dolphin.load_model signature: {last_error}",
            error_code="MODEL_LOAD_FAILED",
        )

    def _ensure_loaded(self, device: str) -> None:
        if self._model is not None and self._loaded_device == device:
            return

        self.validate_model_assets()
        with self._lock:
            if self._model is not None and self._loaded_device == device:
                return

            try:
                import dolphin
            except Exception as exc:
                raise DolphinAsrError(
                    f"failed to import dolphin runtime: {exc}",
                    error_code="MODEL_LOAD_FAILED",
                ) from exc

            model_name = get_settings()["dolphin_model_name"]
            self._dolphin_module = dolphin
            self._transcribe_function = getattr(dolphin, "transcribe", None)
            self._model = self._load_model_from_candidates(
                dolphin,
                model_name=model_name,
                device=device,
            )
            self._loaded_device = device

    def _sanitize_transcript_text(self, text: str) -> str:
        normalized = text.strip()
        normalized = _DOLPHIN_CONTROL_TOKEN_PATTERN.sub("", normalized)
        return normalized.strip()

    def _extract_transcript_text(self, result) -> str:
        if isinstance(result, str):
            return self._sanitize_transcript_text(result)
        if isinstance(result, dict):
            for key in ("text", "transcript", "transcript_text"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return self._sanitize_transcript_text(value)
        for key in ("text", "transcript", "transcript_text"):
            value = getattr(result, key, None)
            if isinstance(value, str) and value.strip():
                return self._sanitize_transcript_text(value)
        raise DolphinAsrError(
            "dolphin did not return transcript text",
            error_code="TRANSCRIPTION_FAILED",
        )

    def _extract_confidence(self, result) -> float | None:
        if isinstance(result, dict):
            value = result.get("confidence")
            if isinstance(value, (float, int)):
                return float(value)
            return None
        value = getattr(result, "confidence", None)
        if isinstance(value, (float, int)):
            return float(value)
        return None

    def _transcribe_once(self, wav_path: Path, device: str) -> DolphinTranscriptionResult:
        self._ensure_loaded(device)
        lang_sym = get_settings()["asr_lang_sym"]
        region_sym = get_settings()["asr_region_sym"]

        try:
            if self._transcribe_function is not None:
                result = self._transcribe_function(
                    self._model,
                    str(wav_path),
                    lang_sym=lang_sym,
                    region_sym=region_sym,
                )
            else:
                load_audio = getattr(self._dolphin_module, "load_audio", None)
                if load_audio is None:
                    raise DolphinAsrError(
                        "dolphin runtime does not expose a transcribe API",
                        error_code="TRANSCRIPTION_FAILED",
                    )
                waveform = load_audio(str(wav_path))
                result = self._model(
                    waveform,
                    lang_sym=lang_sym,
                    region_sym=region_sym,
                )
        except DolphinAsrError:
            raise
        except Exception as exc:
            raise DolphinAsrError(
                f"dolphin transcription failed: {exc}",
                error_code="TRANSCRIPTION_FAILED",
            ) from exc

        return DolphinTranscriptionResult(
            transcript_text=self._extract_transcript_text(result),
            transcript_confidence=self._extract_confidence(result),
            resolved_device=device,
        )

    def transcribe(self, wav_path: Path) -> DolphinTranscriptionResult:
        primary_device = self._resolve_device()
        if primary_device != "cuda" or get_settings()["asr_device"] != "auto":
            return self._transcribe_once(wav_path, primary_device)

        try:
            return self._transcribe_once(wav_path, "cuda")
        except DolphinAsrError as exc:
            if exc.error_code == "MODEL_NOT_READY":
                raise
        return self._transcribe_once(wav_path, "cpu")


_ASR_RUNTIME = DolphinAsrRuntime()


def get_asr_runtime() -> DolphinAsrRuntime:
    return _ASR_RUNTIME
