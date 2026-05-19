from __future__ import annotations

import base64
import io
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.schemas import AudioEmotionInferRequest, FrameEmotionInferRequest, TextEmotionInferRequest
from app.services.non_eeg_runtime import runtime_store
from app.services.responses import error_response, success_response

from infer_audio import MODEL_SAMPLE_RATE, predict_audio, resample_linear  # type: ignore
from infer_face import infer_image as infer_face_image  # type: ignore
from infer_pose import predict_frame as predict_pose_frame  # type: ignore
from infer_text import predict_text  # type: ignore


def decode_base64_image(image_base64: str) -> np.ndarray:
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid_image_base64") from exc
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid_image_bytes")
    return image


def decode_audio_to_16k_mono(audio_base64: str, audio_format: str, sampling_rate: int | None) -> np.ndarray:
    try:
        raw = base64.b64decode(audio_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid_audio_base64") from exc

    fmt = str(audio_format).strip().lower()
    if fmt in {"wav", "flac", "ogg"}:
        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("soundfile_not_installed") from exc
        try:
            audio, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("invalid_audio_bytes") from exc
    elif fmt in {"webm", "mp4", "mpeg"}:
        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("soundfile_not_installed") from exc

        source_suffix = {
            "webm": ".webm",
            "mp4": ".mp4",
            "mpeg": ".mp3",
        }.get(fmt, ".bin")
        with tempfile.TemporaryDirectory(prefix="mcs-audio-") as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / f"source{source_suffix}"
            wav_path = temp_path / "normalized.wav"
            source_path.write_bytes(raw)
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-ac",
                    "1",
                    "-ar",
                    str(MODEL_SAMPLE_RATE),
                    str(wav_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0 or not wav_path.exists():
                raise ValueError("invalid_audio_bytes")
            try:
                audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
            except Exception as exc:  # noqa: BLE001
                raise ValueError("invalid_audio_bytes") from exc
    elif fmt == "pcm_f32le":
        if not sampling_rate or int(sampling_rate) <= 0:
            raise ValueError("invalid_sampling_rate")
        try:
            audio = np.frombuffer(raw, dtype=np.float32)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("invalid_audio_bytes") from exc
        sr = int(sampling_rate)
    else:
        raise ValueError("invalid_audio_format")

    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)
    if audio.size == 0:
        raise ValueError("empty_audio")
    if sr != MODEL_SAMPLE_RATE:
        audio = resample_linear(audio, sr, MODEL_SAMPLE_RATE)
    return audio.astype(np.float32, copy=False)


def build_pose_no_person_result() -> dict:
    return {
        "status": "no_pose",
        "modality": "pose",
        "label": "no_pose",
        "score": 0.0,
        "extra": {},
    }


def infer_text_emotion(request: TextEmotionInferRequest) -> dict:
    if not request.text or not request.text.strip():
        return error_response("empty_text", 4001)
    try:
        engine = runtime_store.get_text_engine()
        result = predict_text(engine, request.text.strip())
        return success_response({"result": result})
    except Exception:  # noqa: BLE001
        return error_response("model_inference_failed", 5001)


def infer_audio_emotion(request: AudioEmotionInferRequest) -> dict:
    try:
        audio_16k = decode_audio_to_16k_mono(request.audio_base64, request.audio_format, request.sampling_rate)
    except RuntimeError as exc:
        return error_response(str(exc), 5002)
    except ValueError as exc:
        return error_response(str(exc), 4002)
    try:
        engine = runtime_store.get_audio_engine()
        result = predict_audio(engine, audio_16k)
        return success_response({"result": result})
    except Exception:  # noqa: BLE001
        return error_response("model_inference_failed", 5001)


def infer_face_emotion(request: FrameEmotionInferRequest) -> dict:
    image_format = request.image_format.strip().lower()
    if image_format not in {"jpg", "jpeg", "png", "bmp"}:
        return error_response("invalid_image_format", 4001)
    try:
        frame = decode_base64_image(request.image_base64)
    except ValueError as exc:
        return error_response(str(exc), 4002)
    try:
        engine = runtime_store.get_face_engine()
        result = infer_face_image(engine, frame)
        return success_response({"result": result})
    except Exception:  # noqa: BLE001
        return error_response("model_inference_failed", 5001)


def infer_pose_emotion(request: FrameEmotionInferRequest) -> dict:
    image_format = request.image_format.strip().lower()
    if image_format not in {"jpg", "jpeg", "png", "bmp"}:
        return error_response("invalid_image_format", 4001)
    try:
        frame = decode_base64_image(request.image_base64)
    except ValueError as exc:
        return error_response(str(exc), 4002)
    try:
        engine = runtime_store.get_pose_engine(request.session_id)
        _, result = predict_pose_frame(engine, frame)
        if result is None:
            result = build_pose_no_person_result()
        return success_response({"result": result})
    except Exception:  # noqa: BLE001
        return error_response("model_inference_failed", 5001)
