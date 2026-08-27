from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import get_settings


HEALTHY_PROCESS_STATUSES = {
    "idle",
    "scanning",
    "connecting",
    "connected",
    "streaming",
    "disconnected",
}


def validate_status_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return "status_payload_is_not_object"
    status = str(payload.get("status") or "").strip()
    if status not in HEALTHY_PROCESS_STATUSES:
        return f"unhealthy_process_status:{status or 'missing'}"
    if not str(payload.get("updated_at") or "").strip():
        return "status_updated_at_missing"
    return None


def check_status_file(status_file: Path) -> str | None:
    try:
        payload = json.loads(status_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return f"status_file_missing:{status_file}"
    except (OSError, json.JSONDecodeError) as exc:
        return f"status_file_invalid:{status_file}:{exc}"
    return validate_status_payload(payload)


def main() -> int:
    status_file = Path(get_settings()["status_file"])
    error = check_status_file(status_file)
    if error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
