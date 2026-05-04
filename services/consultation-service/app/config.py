from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Consultation Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "workflow_resources_dir": os.getenv(
            "WORKFLOW_RESOURCES_DIR",
            "/home/ZR/data2/MCS/packages/workflow-resources",
        ),
        "workflow_id": os.getenv("WORKFLOW_ID", "consultation-v1"),
        "script_bundle": os.getenv("SCRIPT_BUNDLE", "rule-v1"),
        "default_doctor_persona": os.getenv("DEFAULT_DOCTOR_PERSONA", "doctor-a-calm-female"),
    }
