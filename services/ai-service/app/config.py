from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> dict:
    return {
        "app_name": os.getenv("APP_NAME", "AI Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "llm_provider": os.getenv("LLM_PROVIDER", "disabled"),
        "llm_base_url": os.getenv("LLM_BASE_URL", ""),
        "llm_api_key": os.getenv("LLM_API_KEY", ""),
    }
