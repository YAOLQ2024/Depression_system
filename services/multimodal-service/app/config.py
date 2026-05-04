from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Multimodal Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        "multimodal_bucket": os.getenv("MULTIMODAL_BUCKET", "mcs-multimodal"),
    }
