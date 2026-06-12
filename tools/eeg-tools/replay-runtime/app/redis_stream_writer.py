from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_field_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_stream_entry(
    *,
    payload: bytes,
    received_at: datetime,
    device_id: str | None,
    source_name: str,
    payload_encoding: str,
    first_received_at: datetime | None = None,
    packet_count: int = 1,
    extra_fields: dict[str, object] | None = None,
) -> dict[str, str]:
    timestamp_ms = int(received_at.timestamp() * 1000)
    entry = {
        "ts": str(timestamp_ms),
        "received_at": _isoformat(received_at),
        "source": source_name,
        "packet_count": str(max(1, int(packet_count))),
    }
    if first_received_at is not None:
        entry["first_received_at"] = _isoformat(first_received_at)
    if device_id:
        entry["device_id"] = device_id
    normalized_encoding = payload_encoding.strip().lower()
    if normalized_encoding == "base64":
        entry["payload_base64"] = base64.b64encode(payload).decode("ascii")
    else:
        entry["payload_hex"] = payload.hex()
    for key, value in (extra_fields or {}).items():
        if not key or value is None:
            continue
        entry[str(key)] = _normalize_field_value(value)
    return entry


class RedisStreamWriter:
    def __init__(
        self,
        *,
        redis_url: str,
        stream_key: str,
        source_name: str,
        payload_encoding: str,
        maxlen: int,
        approximate_maxlen: bool,
        connect_timeout_seconds: float,
        socket_timeout_seconds: float,
    ) -> None:
        self._redis_url = redis_url
        self._stream_key = stream_key
        self._source_name = source_name
        self._payload_encoding = payload_encoding
        self._maxlen = maxlen
        self._approximate_maxlen = approximate_maxlen
        self._connect_timeout_seconds = connect_timeout_seconds
        self._socket_timeout_seconds = socket_timeout_seconds
        self._client = None

    @property
    def stream_key(self) -> str:
        return self._stream_key

    def _build_client(self) -> Any:
        try:
            from redis import Redis
        except Exception as exc:  # pragma: no cover - exercised in runtime env
            raise RuntimeError(
                "redis_dependency_missing: install tools/eeg-tools/requirements.txt"
            ) from exc
        return Redis.from_url(
            self._redis_url,
            decode_responses=False,
            socket_connect_timeout=self._connect_timeout_seconds,
            socket_timeout=self._socket_timeout_seconds,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def publish(
        self,
        *,
        payload: bytes,
        received_at: datetime,
        device_id: str | None,
        first_received_at: datetime | None = None,
        packet_count: int = 1,
        extra_fields: dict[str, object] | None = None,
    ) -> str:
        entry = build_stream_entry(
            payload=payload,
            received_at=received_at,
            device_id=device_id,
            source_name=self._source_name,
            payload_encoding=self._payload_encoding,
            first_received_at=first_received_at,
            packet_count=packet_count,
            extra_fields=extra_fields,
        )
        client = self._get_client()
        try:
            entry_id = client.xadd(
                self._stream_key,
                entry,
                maxlen=self._maxlen,
                approximate=self._approximate_maxlen,
            )
        except Exception:
            self.close()
            raise
        if isinstance(entry_id, bytes):
            return entry_id.decode("utf-8", errors="ignore")
        return str(entry_id)

    def close(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        close_method = getattr(client, "close", None)
        if callable(close_method):
            close_method()
