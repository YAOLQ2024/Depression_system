from __future__ import annotations

from datetime import datetime, timezone


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def success_response(data: dict | None = None, message: str = "ok") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": data or {},
        "timestamp": _timestamp(),
    }
