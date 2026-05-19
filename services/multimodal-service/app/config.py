from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


@lru_cache(maxsize=1)
def get_settings() -> dict:
    service_root = Path(__file__).resolve().parents[1]
    runtime_assets_dir = Path(
        os.getenv(
            "RUNTIME_ASSETS_DIR",
            str(service_root / "runtime-assets"),
        )
    )
    model_root = runtime_assets_dir / "models"

    return {
        "app_name": os.getenv("APP_NAME", "Multimodal Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        "minio_access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "minio_secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        "minio_secure": _as_bool(os.getenv("MINIO_SECURE"), False),
        "multimodal_bucket": os.getenv("MULTIMODAL_BUCKET", "mcs-multimodal"),
        "runtime_assets_dir": runtime_assets_dir,
        "dolphin_model_name": os.getenv("DOLPHIN_MODEL_NAME", "base.cn"),
        "dolphin_model_dir": Path(
            os.getenv(
                "DOLPHIN_MODEL_DIR",
                str(runtime_assets_dir / "asr" / "base.cn"),
            )
        ),
        "asr_device": os.getenv("ASR_DEVICE", "auto").strip().lower() or "auto",
        "asr_sync_timeout_ms": _as_int(
            os.getenv("ASR_SYNC_TIMEOUT_MS"),
            15000,
        ),
        "asr_lang_sym": os.getenv("ASR_LANG_SYM", "zh"),
        "asr_region_sym": os.getenv("ASR_REGION_SYM", "CN"),
        "upload_max_bytes": 25 * 1024 * 1024,
        "upload_max_duration_ms": 60_000,
        "upload_processing_dir": runtime_assets_dir / "tmp",
        "model_provider": os.getenv("MODEL_PROVIDER", "CPUExecutionProvider"),
        "pose_window": int(os.getenv("POSE_WINDOW", "96")),
        "model_root": str(model_root),
        "text_model_dir": str(model_root / "text_emotion"),
        "audio_model_dir": str(model_root / "audio_emotion"),
        "face_model_dir": str(model_root / "face_emotion"),
        "pose_model_dir": str(model_root / "pose_emotion"),
    }
