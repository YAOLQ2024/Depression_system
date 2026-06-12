from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class JsonlRecorder:
    def __init__(self, *, enabled: bool, record_dir: Path, source_name: str) -> None:
        self._enabled = enabled
        self._record_dir = Path(record_dir)
        self._source_name = source_name
        self._lock = threading.Lock()
        self._handle = None
        self._record_file: Path | None = None

    @property
    def record_file(self) -> Path | None:
        return self._record_file

    def _ensure_open(self) -> None:
        if not self._enabled or self._handle is not None:
            return
        self._record_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._record_file = self._record_dir / f"eeg-host-bridge-{timestamp}.jsonl"
        self._handle = self._record_file.open("a", encoding="utf-8")

    def record(self, *, payload: bytes, received_at: datetime, device_id: str | None) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._ensure_open()
            assert self._handle is not None
            self._handle.write(
                json.dumps(
                    {
                        "received_at": _isoformat(received_at),
                        "device_id": device_id,
                        "payload_hex": payload.hex(),
                        "payload_size": len(payload),
                        "source": self._source_name,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            self._handle.flush()

    def close(self) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.close()
                self._handle = None

