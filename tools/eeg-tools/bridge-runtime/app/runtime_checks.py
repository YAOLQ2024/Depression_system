from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


DEFAULT_SYSTEM_DBUS_SOCKET = Path("/run/dbus/system_bus_socket")


def validate_system_dbus_socket(path: Path = DEFAULT_SYSTEM_DBUS_SOCKET) -> list[str]:
    """Validate the host system D-Bus socket used by Bleak on Linux."""
    if not path.exists():
        return [f"system_dbus_socket_missing:{path}"]
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        return [f"system_dbus_socket_unreadable:{path}:{exc}"]
    if not stat.S_ISSOCK(mode):
        return [f"system_dbus_path_is_not_socket:{path}"]
    return []


def validate_runtime_environment() -> list[str]:
    """Run only checks required before starting the BLE bridge.

    Windows uses the same bridge runtime through WinRT and therefore must not be
    required to expose the Linux system D-Bus socket.
    """
    if not sys.platform.startswith("linux"):
        return []
    socket_path = Path(
        os.getenv("EEG_HOST_BRIDGE_SYSTEM_DBUS_SOCKET", str(DEFAULT_SYSTEM_DBUS_SOCKET))
    )
    return validate_system_dbus_socket(socket_path)
