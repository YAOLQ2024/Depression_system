from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from app.config import get_settings
from app.redis import build_redis_key, get_optional_redis_client

logger = logging.getLogger(__name__)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw_value: bytes | str | None) -> dict[str, Any] | None:
    if raw_value in (None, b"", ""):
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8")
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def build_eeg_live_key(session_id: str) -> str:
    return build_redis_key("eeg", "live", session_id)


def build_eeg_turn_state_key(session_id: str, turn_id: str) -> str:
    return build_redis_key("eeg", "turn", session_id, turn_id, "state")


def build_eeg_turn_window_key(session_id: str, turn_id: str, window_index: int) -> str:
    return build_redis_key("eeg", "turn", session_id, turn_id, "window", str(window_index))


def read_eeg_live_payload(session_id: str) -> dict[str, Any] | None:
    client = get_optional_redis_client()
    if client is None:
        return None
    try:
        return _json_loads(client.get(build_eeg_live_key(session_id)))
    except Exception:
        logger.warning("eeg redis live read failed for session_id=%s", session_id, exc_info=True)
        return None


def write_eeg_live_payload(session_id: str, payload: dict[str, Any]) -> bool:
    client = get_optional_redis_client()
    if client is None:
        return False
    settings = get_settings()
    try:
        client.set(
            build_eeg_live_key(session_id),
            _json_dumps(payload),
            ex=int(settings["eeg_live_ttl_seconds"]),
        )
        return True
    except Exception:
        logger.warning("eeg redis live write failed for session_id=%s", session_id, exc_info=True)
        return False


def write_eeg_turn_state_payload(session_id: str, turn_id: str, payload: dict[str, Any]) -> bool:
    client = get_optional_redis_client()
    if client is None:
        return False
    settings = get_settings()
    try:
        client.set(
            build_eeg_turn_state_key(session_id, turn_id),
            _json_dumps(payload),
            ex=int(settings["eeg_turn_state_ttl_seconds"]),
        )
        return True
    except Exception:
        logger.warning(
            "eeg redis turn-state write failed for session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False


def write_eeg_turn_window_payload(
    session_id: str,
    turn_id: str,
    window_index: int,
    payload: dict[str, Any],
) -> bool:
    client = get_optional_redis_client()
    if client is None:
        return False
    settings = get_settings()
    try:
        client.set(
            build_eeg_turn_window_key(session_id, turn_id, window_index),
            _json_dumps(payload),
            ex=int(settings["eeg_turn_window_ttl_seconds"]),
        )
        return True
    except Exception:
        logger.warning(
            "eeg redis window write failed for session_id=%s turn_id=%s window_index=%s",
            session_id,
            turn_id,
            window_index,
            exc_info=True,
        )
        return False


def clear_eeg_turn_hot_state(
    session_id: str,
    turn_id: str,
    *,
    window_indexes: Sequence[int] | None = None,
) -> bool:
    client = get_optional_redis_client()
    if client is None:
        return False
    keys = [build_eeg_turn_state_key(session_id, turn_id)]
    for window_index in window_indexes or []:
        keys.append(build_eeg_turn_window_key(session_id, turn_id, int(window_index)))
    try:
        if keys:
            client.delete(*keys)
        return True
    except Exception:
        logger.warning(
            "eeg redis cleanup failed for session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False
