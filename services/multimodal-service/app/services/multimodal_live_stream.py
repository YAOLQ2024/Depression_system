from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from app.redis import build_redis_key, get_optional_redis_client

logger = logging.getLogger(__name__)

LIVE_STREAM_HEARTBEAT_SECONDS = 15.0
LIVE_STREAM_RECONCILE_SECONDS = 5.0
LIVE_STREAM_PUBSUB_TIMEOUT_SECONDS = 1.0
LIVE_STREAM_POLL_SECONDS = 1.0


def build_multimodal_live_channel(session_id: str) -> str:
    return build_redis_key("live", "stream", session_id)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw_value: bytes | str | None) -> dict[str, Any] | None:
    if raw_value in (None, b"", ""):
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8")
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _encode_sse_event(event: str, payload: dict[str, Any]) -> str:
    lines = [f"event: {event}"]
    encoded_payload = _json_dumps(payload)
    for line in encoded_payload.splitlines() or ["{}"]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


def _should_emit_snapshot(
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
) -> bool:
    if snapshot is None:
        return False
    if previous_snapshot is None:
        return True
    return snapshot != previous_snapshot


def publish_multimodal_live_snapshot(
    session_id: str,
    snapshot: dict[str, Any],
) -> bool:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning(
            "multimodal live stream redis init failed session_id=%s",
            session_id,
            exc_info=True,
        )
        return False

    if client is None:
        return False

    try:
        client.publish(
            build_multimodal_live_channel(session_id),
            _json_dumps(snapshot),
        )
        return True
    except Exception:
        logger.warning(
            "multimodal live stream publish failed session_id=%s",
            session_id,
            exc_info=True,
        )
        return False


async def iter_multimodal_live_events(
    *,
    session_id: str,
    initial_snapshot: dict[str, Any],
    snapshot_loader: Callable[[], dict[str, Any]],
    disconnect_checker: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[str]:
    last_snapshot = dict(initial_snapshot)
    last_heartbeat_at = time.monotonic()
    last_reconcile_at = last_heartbeat_at

    yield _encode_sse_event("live_snapshot", last_snapshot)

    pubsub = None
    try:
        try:
            client = get_optional_redis_client()
        except Exception:
            logger.warning(
                "multimodal live stream redis init failed session_id=%s",
                session_id,
                exc_info=True,
            )
            client = None

        if client is not None:
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            await asyncio.to_thread(
                pubsub.subscribe,
                build_multimodal_live_channel(session_id),
            )

        while True:
            if disconnect_checker is not None and await disconnect_checker():
                break

            published_snapshot: dict[str, Any] | None = None
            if pubsub is not None:
                try:
                    message = await asyncio.to_thread(
                        pubsub.get_message,
                        timeout=LIVE_STREAM_PUBSUB_TIMEOUT_SECONDS,
                    )
                except Exception:
                    logger.warning(
                        "multimodal live stream pubsub read failed session_id=%s",
                        session_id,
                        exc_info=True,
                    )
                    message = None
                if message is not None and message.get("type") == "message":
                    published_snapshot = _json_loads(message.get("data"))
            else:
                await asyncio.sleep(LIVE_STREAM_POLL_SECONDS)

            if _should_emit_snapshot(published_snapshot, last_snapshot):
                last_snapshot = dict(published_snapshot or {})
                yield _encode_sse_event("live_snapshot", last_snapshot)
                last_heartbeat_at = time.monotonic()

            now = time.monotonic()
            if now - last_reconcile_at >= LIVE_STREAM_RECONCILE_SECONDS:
                last_reconcile_at = now
                try:
                    reconciled_snapshot = await asyncio.to_thread(snapshot_loader)
                except Exception:
                    logger.warning(
                        "multimodal live stream reconcile failed session_id=%s",
                        session_id,
                        exc_info=True,
                    )
                    reconciled_snapshot = None
                if _should_emit_snapshot(reconciled_snapshot, last_snapshot):
                    last_snapshot = dict(reconciled_snapshot or {})
                    yield _encode_sse_event("live_snapshot", last_snapshot)
                    last_heartbeat_at = time.monotonic()

            if now - last_heartbeat_at >= LIVE_STREAM_HEARTBEAT_SECONDS:
                yield _encode_sse_event(
                    "heartbeat",
                    {
                        "session_id": session_id,
                        "updated_at": last_snapshot.get("updated_at"),
                    },
                )
                last_heartbeat_at = time.monotonic()
    finally:
        if pubsub is not None:
            try:
                await asyncio.to_thread(pubsub.close)
            except Exception:
                logger.warning(
                    "multimodal live stream pubsub close failed session_id=%s",
                    session_id,
                    exc_info=True,
                )
