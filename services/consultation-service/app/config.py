from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme:
        return parsed.netloc
    return endpoint


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Consultation Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "multimodal_service_url": os.getenv(
            "MULTIMODAL_SERVICE_URL",
            "http://127.0.0.1:8017",
        ),
        "workflow_resources_dir": os.getenv(
            "WORKFLOW_RESOURCES_DIR",
            "/home/ZR/data2/MCS/packages/workflow-resources",
        ),
        "workflow_id": os.getenv("WORKFLOW_ID", "consultation-v1"),
        "script_bundle": os.getenv("SCRIPT_BUNDLE", "rule-v1"),
        "default_doctor_persona": os.getenv("DEFAULT_DOCTOR_PERSONA", "doctor-a-calm-female"),
        "minio_endpoint": _normalize_endpoint(os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000")),
        "minio_access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "minio_secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        "minio_secure": _as_bool(os.getenv("MINIO_SECURE"), False),
        "consultation_bucket": os.getenv("CONSULTATION_BUCKET", "mcs-consultation"),
        "speech_emotion_model_name": os.getenv("SPEECH_EMOTION_MODEL_NAME", "audio_emotion"),
        "speech_emotion_model_version": os.getenv("SPEECH_EMOTION_MODEL_VERSION", "v1"),
    }
