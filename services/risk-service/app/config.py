from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Risk Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "consultation_service_url": os.getenv(
            "CONSULTATION_SERVICE_URL",
            "http://127.0.0.1:8012",
        ),
        "assessment_service_url": os.getenv(
            "ASSESSMENT_SERVICE_URL",
            "http://127.0.0.1:8013",
        ),
        "multimodal_service_url": os.getenv(
            "MULTIMODAL_SERVICE_URL",
            "http://127.0.0.1:8017",
        ),
    }
