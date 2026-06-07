from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _default_workflow_resources_dir(service_root: Path) -> Path:
    try:
        workspace_root = service_root.parents[1]
        source_dir = workspace_root / "packages" / "workflow-resources"
        if source_dir.exists():
            return source_dir
    except IndexError:
        pass

    container_dir = service_root / "workflow-resources"
    if container_dir.exists():
        return container_dir

    return service_root / "workflow-resources"


@lru_cache(maxsize=1)
def get_settings() -> dict:
    service_root = Path(__file__).resolve().parents[1]
    return {
        "app_name": os.getenv("APP_NAME", "Assessment Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "multimodal_service_url": os.getenv(
            "MULTIMODAL_SERVICE_URL",
            "http://127.0.0.1:8017",
        ),
        "risk_service_url": os.getenv(
            "RISK_SERVICE_URL",
            "http://127.0.0.1:8014",
        ),
        "workflow_resources_dir": str(
            Path(
                os.getenv(
                    "WORKFLOW_RESOURCES_DIR",
                    str(_default_workflow_resources_dir(service_root)),
                )
            )
        ),
        "active_scale_set": os.getenv("ACTIVE_SCALE_SET", "v1"),
        "active_scale_slugs": [
            slug.strip()
            for slug in os.getenv(
                "ACTIVE_SCALE_SLUGS",
                "phq9,sds,sas,social-function",
            ).split(",")
            if slug.strip()
        ],
    }
