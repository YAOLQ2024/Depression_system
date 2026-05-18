from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _default_workflow_resources_dir(service_root: Path) -> Path:
    # Source checkout layout: <mcs-root>/services/gateway-service/app/config.py
    try:
        workspace_root = service_root.parents[1]
        source_dir = workspace_root / "packages" / "workflow-resources"
        if source_dir.exists():
            return source_dir
    except IndexError:
        pass

    # Container layout used by docker compose: /app/workflow-resources
    container_dir = service_root / "workflow-resources"
    if container_dir.exists():
        return container_dir

    # Safe fallback when neither path exists yet.
    return service_root / "workflow-resources"


@lru_cache(maxsize=1)
def get_settings() -> dict:
    service_root = Path(__file__).resolve().parents[1]
    return {
        "app_name": os.getenv("APP_NAME", "Gateway Service"),
        "identity_service_url": os.getenv("IDENTITY_SERVICE_URL", "http://127.0.0.1:8011"),
        "consultation_service_url": os.getenv("CONSULTATION_SERVICE_URL", "http://127.0.0.1:8012"),
        "assessment_service_url": os.getenv("ASSESSMENT_SERVICE_URL", "http://127.0.0.1:8013"),
        "multimodal_service_url": os.getenv("MULTIMODAL_SERVICE_URL", "http://127.0.0.1:8017"),
        "session_cookie_name": os.getenv("SESSION_COOKIE_NAME", "mcs_session"),
        "workflow_resources_dir": Path(
            os.getenv(
                "WORKFLOW_RESOURCES_DIR",
                str(_default_workflow_resources_dir(service_root)),
            )
        ),
        "cors_origins": [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:3001,http://localhost:3001",
            ).split(",")
            if origin.strip()
        ],
        "cors_origin_regex": os.getenv("CORS_ORIGIN_REGEX", r"^https?://[^/]+:(3000|3001)$") or None,
    }
