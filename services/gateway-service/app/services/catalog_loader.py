from __future__ import annotations

from pathlib import Path

import yaml

from app.config import get_settings


def _resources_dir() -> Path:
    return Path(get_settings()["workflow_resources_dir"])


def load_doctor_personas() -> list[dict]:
    items = []
    persona_dir = _resources_dir() / "doctor-personas"
    for path in sorted(persona_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            items.append(yaml.safe_load(handle) or {})
    return items


def load_workflow_summary() -> dict:
    workflow_path = _resources_dir() / "workflows" / "consultation-v1.yaml"
    with workflow_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return {
        "workflow_id": payload.get("workflow_id"),
        "title": payload.get("title"),
        "status": payload.get("status"),
        "entry_stage": payload.get("entry_stage"),
        "stage_count": len(payload.get("stages") or []),
        "stages": [
            {
                "id": stage.get("id"),
                "name": stage.get("name"),
                "type": stage.get("type"),
            }
            for stage in (payload.get("stages") or [])
        ],
    }
