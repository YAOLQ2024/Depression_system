from __future__ import annotations

import importlib
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class ReplayWriterTests(unittest.TestCase):
    def test_build_stream_entry_with_hex_payload(self) -> None:
        with activated_tool_app("replay-runtime"):
            writer = importlib.import_module("app.redis_stream_writer")
            received_at = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
            first_received_at = datetime(2026, 6, 8, 11, 59, 59, 500000, tzinfo=timezone.utc)
            payload = writer.build_stream_entry(
                payload=b"\x01\x02\x03",
                received_at=received_at,
                device_id="EE:01",
                source_name="eeg_replay",
                payload_encoding="hex",
                first_received_at=first_received_at,
                packet_count=4,
                extra_fields={"replay_mode": "raw"},
            )
            self.assertEqual(payload["device_id"], "EE:01")
            self.assertEqual(payload["payload_hex"], "010203")
            self.assertEqual(payload["source"], "eeg_replay")
            self.assertEqual(payload["received_at"], "2026-06-08T12:00:00Z")
            self.assertEqual(payload["first_received_at"], "2026-06-08T11:59:59.500000Z")
            self.assertEqual(payload["packet_count"], "4")
            self.assertEqual(payload["replay_mode"], "raw")

    def test_build_stream_entry_with_base64_payload(self) -> None:
        with activated_tool_app("replay-runtime"):
            writer = importlib.import_module("app.redis_stream_writer")
            received_at = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
            payload = writer.build_stream_entry(
                payload=b"\x01\x02\x03",
                received_at=received_at,
                device_id=None,
                source_name="eeg_replay",
                payload_encoding="base64",
            )
            self.assertEqual(payload["payload_base64"], "AQID")
            self.assertNotIn("device_id", payload)


if __name__ == "__main__":
    unittest.main()
