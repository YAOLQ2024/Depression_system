from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "Followup Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "report_export_dir": os.getenv(
            "REPORT_EXPORT_DIR",
            "/home/ZR/data2/MCS/data/reports",
        ),
    }
