from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BridgeHealthStore:
    def __init__(self, status_file: Path) -> None:
        self._status_file = Path(status_file)
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._payload: dict[str, Any] = {}

    def update(self, **fields: Any) -> None:
        with self._lock:
            self._payload.update(fields)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._payload)

    def write(self, *, retries: int = 3, retry_delay_seconds: float = 0.05) -> None:
        with self._lock:
            payload = dict(self._payload)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        self._status_file.parent.mkdir(parents=True, exist_ok=True)

        last_error: Exception | None = None
        with self._write_lock:
            for attempt in range(max(1, retries)):
                temp_file = self._status_file.with_name(
                    f"{self._status_file.name}.{uuid.uuid4().hex}.tmp"
                )
                try:
                    temp_file.write_text(serialized, encoding="utf-8")
                    os.replace(temp_file, self._status_file)
                    return
                except PermissionError as exc:
                    last_error = exc
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except OSError:
                        logger.warning(
                            "EEG host bridge failed to clean temp health file path=%s",
                            temp_file,
                            exc_info=True,
                        )
                    if attempt + 1 >= max(1, retries):
                        break
                    time.sleep(max(0.0, retry_delay_seconds))
                except Exception:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except OSError:
                        logger.warning(
                            "EEG host bridge failed to clean temp health file path=%s",
                            temp_file,
                            exc_info=True,
                        )
                    raise
        if last_error is not None:
            raise last_error
