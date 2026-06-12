from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class ReplayConfigTests(unittest.TestCase):
    def test_derive_stream_key_appends_default_suffix_for_transport_prefix(self) -> None:
        with activated_tool_app("replay-runtime"):
            config = importlib.import_module("app.config")
            self.assertEqual(
                config.derive_stream_key(
                    stream_key="",
                    stream_key_prefix="mcs:eeg:transport",
                ),
                "mcs:eeg:transport:default",
            )

    def test_derive_stream_key_keeps_explicit_stream_key(self) -> None:
        with activated_tool_app("replay-runtime"):
            config = importlib.import_module("app.config")
            self.assertEqual(
                config.derive_stream_key(
                    stream_key="mcs:eeg:transport:device-1",
                    stream_key_prefix="mcs:eeg:transport",
                ),
                "mcs:eeg:transport:device-1",
            )


if __name__ == "__main__":
    unittest.main()
