from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_settings() -> dict:
    app_dir = Path(__file__).resolve().parent
    model_root = app_dir / "models" / "non_eeg"
    return {
        "app_name": os.getenv("APP_NAME", "Multimodal Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        "multimodal_bucket": os.getenv("MULTIMODAL_BUCKET", "mcs-multimodal"),
        "model_provider": os.getenv("MODEL_PROVIDER", "CPUExecutionProvider"),
        "pose_window": int(os.getenv("POSE_WINDOW", "96")),
        "model_root": str(model_root),
        "text_model_dir": str(model_root / "text_emotion"),
        "audio_model_dir": str(model_root / "audio_emotion"),
        "face_model_dir": str(model_root / "face_emotion"),
        "pose_model_dir": str(model_root / "pose_emotion"),
    }
