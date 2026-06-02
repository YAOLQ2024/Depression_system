from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings


class RiskResourceError(Exception):
    pass


def _resources_dir() -> Path:
    return Path(get_settings()["workflow_resources_dir"])


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RiskResourceError(f"resource not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise RiskResourceError(f"invalid yaml resource: {path}") from exc
    if not isinstance(payload, dict):
        raise RiskResourceError(f"yaml resource must be an object: {path}")
    return payload


@lru_cache(maxsize=8)
def load_risk_rule_set(rule_set_id: str) -> dict[str, Any]:
    normalized_rule_set_id = str(rule_set_id or "").strip()
    if not normalized_rule_set_id:
        raise RiskResourceError("risk rule set id is required")
    path = _resources_dir() / "risk-rules" / f"{normalized_rule_set_id}.yaml"
    return _load_yaml(path)


@lru_cache(maxsize=1)
def load_intervention_catalog() -> dict[str, Any]:
    path = _resources_dir() / "intervention-programs" / "catalog.yaml"
    return _load_yaml(path)
