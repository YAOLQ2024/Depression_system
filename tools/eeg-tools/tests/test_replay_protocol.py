from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class ReplayProtocolTests(unittest.TestCase):
    def test_build_wave_frame_has_expected_size(self) -> None:
        with activated_tool_app("replay-runtime"):
            protocol = importlib.import_module("app.protocol")
            frame = protocol.build_wave_frame(7, [0.1, -0.2, 0.3])
            self.assertEqual(len(frame), protocol.WAVE_PACKET_BYTES)
            self.assertEqual(frame[:3], b"\x06\x09\x01")

    def test_build_feature_frame_has_expected_size(self) -> None:
        with activated_tool_app("replay-runtime"):
            protocol = importlib.import_module("app.protocol")
            frame = protocol.build_feature_frame([float(index) for index in range(57)])
            self.assertEqual(len(frame), protocol.FEATURE_PACKET_BYTES)
            self.assertEqual(frame[:3], b"\x06\x09\x02")

    def test_generators_return_expected_shapes(self) -> None:
        with activated_tool_app("replay-runtime"):
            protocol = importlib.import_module("app.protocol")
            self.assertEqual(len(protocol.generate_wave_channels(0.25, amplitude=20.0)), 3)
            self.assertEqual(len(protocol.generate_feature_vector(0.25)), 57)


if __name__ == "__main__":
    unittest.main()
