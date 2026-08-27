from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class BridgeConfigTests(unittest.TestCase):
    def test_derive_stream_key_appends_default_suffix_for_transport_prefix(self) -> None:
        with activated_tool_app("bridge-runtime"):
            config = importlib.import_module("app.config")
            self.assertEqual(
                config.derive_stream_key(
                    stream_key="",
                    stream_key_prefix="mcs:eeg:transport",
                ),
                "mcs:eeg:transport:default",
            )

    def test_derive_stream_key_keeps_explicit_stream_key(self) -> None:
        with activated_tool_app("bridge-runtime"):
            config = importlib.import_module("app.config")
            self.assertEqual(
                config.derive_stream_key(
                    stream_key="mcs:eeg:transport:device-1",
                    stream_key_prefix="mcs:eeg:transport",
                ),
                "mcs:eeg:transport:device-1",
            )

    def test_protocol_defaults_remain_compatible_with_host_bridge(self) -> None:
        protocol_variables = {
            "EEG_STREAM_KEY_PREFIX",
            "EEG_HOST_BRIDGE_STREAM_KEY",
            "EEG_HOST_BRIDGE_SOURCE",
            "EEG_HOST_BRIDGE_PAYLOAD_ENCODING",
            "EEG_HOST_BRIDGE_PUBLISH_BATCH_SIZE",
            "EEG_HOST_BRIDGE_PUBLISH_BATCH_TIMEOUT_MS",
        }
        clean_environment = {
            key: value for key, value in os.environ.items() if key not in protocol_variables
        }
        with patch.dict(os.environ, clean_environment, clear=True):
            with activated_tool_app("bridge-runtime"):
                config = importlib.import_module("app.config")
                config.get_settings.cache_clear()
                settings = config.get_settings()
                self.assertEqual(settings["stream_key"], "mcs:eeg:transport:default")
                self.assertEqual(settings["source_name"], "windows_host_bridge")
                self.assertEqual(settings["payload_encoding"], "hex")
                self.assertEqual(settings["publish_batch_size"], 32)
                self.assertEqual(settings["publish_batch_timeout_ms"], 20)


if __name__ == "__main__":
    unittest.main()
