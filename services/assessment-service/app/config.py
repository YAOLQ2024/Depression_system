from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Assessment Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "workflow_resources_dir": os.getenv(
            "WORKFLOW_RESOURCES_DIR",
            "/home/ZR/data2/MCS/packages/workflow-resources",
        ),
        "active_scale_set": os.getenv("ACTIVE_SCALE_SET", "v1"),
    }
