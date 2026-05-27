from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings

if TYPE_CHECKING:
    from redis import Redis

_REDIS_CLIENT: Redis | None = None


def get_redis_url() -> str:
    return str(get_settings()["redis_url"])


def get_redis_key_prefix() -> str:
    return str(get_settings()["redis_key_prefix"])


def is_redis_enabled() -> bool:
    return bool(get_settings()["redis_enabled"])


def get_redis_client() -> Redis:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        from redis import Redis

        settings = get_settings()
        _REDIS_CLIENT = Redis.from_url(
            get_redis_url(),
            socket_timeout=settings["redis_socket_timeout_seconds"],
            socket_connect_timeout=settings["redis_connect_timeout_seconds"],
            health_check_interval=settings["redis_health_check_interval_seconds"],
            decode_responses=False,
        )
    return _REDIS_CLIENT


def get_optional_redis_client() -> Redis | None:
    if not is_redis_enabled():
        return None
    return get_redis_client()


def build_redis_key(*parts: str) -> str:
    normalized_parts = [get_redis_key_prefix()]
    normalized_parts.extend(str(part).strip(":") for part in parts if str(part).strip(":"))
    return ":".join(normalized_parts)


def ping_redis() -> bool:
    client = get_optional_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


def close_redis_client() -> None:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        return
    try:
        _REDIS_CLIENT.close()
    finally:
        _REDIS_CLIENT = None
