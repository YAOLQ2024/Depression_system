from __future__ import annotations

import importlib
import socket
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class BridgeRuntimeChecksTests(unittest.TestCase):
    def test_missing_system_dbus_socket_is_reported(self) -> None:
        with activated_tool_app("bridge-runtime"):
            runtime_checks = importlib.import_module("app.runtime_checks")
            with tempfile.TemporaryDirectory() as temp_dir:
                missing_path = Path(temp_dir) / "system_bus_socket"
                self.assertEqual(
                    runtime_checks.validate_system_dbus_socket(missing_path),
                    [f"system_dbus_socket_missing:{missing_path}"],
                )

    def test_regular_file_is_not_accepted_as_system_dbus_socket(self) -> None:
        with activated_tool_app("bridge-runtime"):
            runtime_checks = importlib.import_module("app.runtime_checks")
            with tempfile.TemporaryDirectory() as temp_dir:
                regular_file = Path(temp_dir) / "system_bus_socket"
                regular_file.touch()
                self.assertEqual(
                    runtime_checks.validate_system_dbus_socket(regular_file),
                    [f"system_dbus_path_is_not_socket:{regular_file}"],
                )

    def test_unix_socket_is_accepted(self) -> None:
        with activated_tool_app("bridge-runtime"):
            runtime_checks = importlib.import_module("app.runtime_checks")
            with tempfile.TemporaryDirectory() as temp_dir:
                socket_path = Path(temp_dir) / "system_bus_socket"
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    server.bind(str(socket_path))
                    self.assertEqual(runtime_checks.validate_system_dbus_socket(socket_path), [])
                finally:
                    server.close()


if __name__ == "__main__":
    unittest.main()
