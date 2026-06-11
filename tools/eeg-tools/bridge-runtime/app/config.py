from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_ENV_FILES_LOADED = False


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_quotes(value.strip())
    return values


def _resolve_runtime_root(default_repo_root: Path) -> Path:
    override = str(os.getenv("MCS_EEG_TOOLS_ROOT") or "").strip()
    if not override:
        return default_repo_root
    return Path(override).resolve()


def load_default_env_files() -> None:
    global _ENV_FILES_LOADED
    if _ENV_FILES_LOADED:
        return

    tool_root = Path(__file__).resolve().parents[1]
    suite_root = Path(__file__).resolve().parents[2]
    default_repo_root = Path(__file__).resolve().parents[4]
    repo_root = _resolve_runtime_root(default_repo_root)
    env_files = [
        repo_root / ".env",
        repo_root / "tools/eeg-tools/.env",
        suite_root / ".env",
    ]
    protected_keys = set(os.environ.keys())
    loaded_values: dict[str, str] = {}
    for env_file in env_files:
        for key, value in _parse_env_file(env_file).items():
            if key in protected_keys:
                continue
            loaded_values[key] = value
    for key, value in loaded_values.items():
        os.environ[key] = value
    _ENV_FILES_LOADED = True


def derive_stream_key(*, stream_key: str | None, stream_key_prefix: str) -> str:
    configured_stream_key = str(stream_key or "").strip()
    if configured_stream_key:
        return configured_stream_key
    normalized_prefix = str(stream_key_prefix).strip() or "mcs:eeg:transport"
    if normalized_prefix.rsplit(":", 1)[-1] == "transport":
        return f"{normalized_prefix}:default"
    return normalized_prefix


def _resolve_repo_relative_path(value: str, repo_root: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


@lru_cache(maxsize=1)
def get_settings() -> dict[str, object]:
    load_default_env_files()
    tool_root = Path(__file__).resolve().parents[1]
    repo_root = _resolve_runtime_root(Path(__file__).resolve().parents[4])

    shared_stream_key_prefix = os.getenv("EEG_STREAM_KEY_PREFIX", "mcs:eeg:transport").strip()
    stream_key = derive_stream_key(
        stream_key=os.getenv("EEG_HOST_BRIDGE_STREAM_KEY"),
        stream_key_prefix=shared_stream_key_prefix,
    )

    return {
        "app_name": os.getenv("EEG_HOST_BRIDGE_APP_NAME", "eeg-host-bridge").strip()
        or "eeg-host-bridge",
        "repo_root": repo_root,
        "tool_root": tool_root,
        "redis_url": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0").strip()
        or "redis://127.0.0.1:6379/0",
        "redis_connect_timeout_seconds": _as_float(
            os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS"),
            2.0,
        ),
        "redis_socket_timeout_seconds": _as_float(
            os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS"),
            2.0,
        ),
        "stream_key_prefix": shared_stream_key_prefix or "mcs:eeg:transport",
        "stream_key": stream_key,
        "source_name": os.getenv("EEG_HOST_BRIDGE_SOURCE", "windows_host_bridge").strip()
        or "windows_host_bridge",
        "payload_encoding": os.getenv("EEG_HOST_BRIDGE_PAYLOAD_ENCODING", "hex").strip().lower()
        or "hex",
        "redis_maxlen": _as_int(os.getenv("EEG_HOST_BRIDGE_REDIS_MAXLEN"), 5000),
        "redis_approx_maxlen": _as_bool(
            os.getenv("EEG_HOST_BRIDGE_REDIS_APPROX_MAXLEN"),
            True,
        ),
        "ble_device_name_hint": os.getenv("EEG_DEVICE_NAME_HINT", "EEG").strip() or "EEG",
        "ble_notify_char_uuid": (
            os.getenv("EEG_NOTIFY_CHAR_UUID", "6e400003-b5a3-f393-e0a9-e50e24dcca9e").strip()
            or "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
        ),
        "ble_scan_seconds": _as_float(os.getenv("EEG_SCAN_SECONDS"), 5.0),
        "reconnect_delay_seconds": _as_float(os.getenv("EEG_RECONNECT_DELAY_SECONDS"), 5.0),
        "queue_maxsize": max(1, _as_int(os.getenv("EEG_HOST_BRIDGE_QUEUE_MAXSIZE"), 2048)),
        "publish_batch_size": max(
            1,
            _as_int(os.getenv("EEG_HOST_BRIDGE_PUBLISH_BATCH_SIZE"), 32),
        ),
        "publish_batch_timeout_ms": max(
            1,
            _as_int(os.getenv("EEG_HOST_BRIDGE_PUBLISH_BATCH_TIMEOUT_MS"), 20),
        ),
        "record_enabled": _as_bool(
            os.getenv("EEG_HOST_BRIDGE_RECORD_ENABLED"),
            False,
        ),
        "record_dir": _resolve_repo_relative_path(
            os.getenv(
                "EEG_HOST_BRIDGE_RECORD_DIR",
                "tools/eeg-tools/data/records",
            ),
            repo_root,
        ),
        "status_file": _resolve_repo_relative_path(
            os.getenv(
                "EEG_HOST_BRIDGE_STATUS_FILE",
                "tools/eeg-tools/tmp/status.json",
            ),
            repo_root,
        ),
        "health_flush_interval_seconds": _as_float(
            os.getenv("EEG_HOST_BRIDGE_HEALTH_FLUSH_INTERVAL_SECONDS"),
            1.0,
        ),
        "queue_full_warning_interval_seconds": _as_float(
            os.getenv("EEG_HOST_BRIDGE_QUEUE_FULL_WARNING_INTERVAL_SECONDS"),
            1.0,
        ),
        "log_level": os.getenv("EEG_HOST_BRIDGE_LOG_LEVEL", "INFO").strip().upper() or "INFO",
    }
