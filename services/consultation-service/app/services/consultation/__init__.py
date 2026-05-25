from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ConsultationServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _ensure_json_list(value: list[Any] | None) -> list[Any]:
    return list(value or [])


__all__ = [
    "ConsultationServiceError",
    "_ensure_json_dict",
    "_ensure_json_list",
    "_now",
]
