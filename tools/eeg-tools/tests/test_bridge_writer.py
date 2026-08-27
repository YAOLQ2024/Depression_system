from __future__ import annotations

import importlib
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class BridgeWriterTests(unittest.TestCase):
    def test_build_stream_entry_with_hex_payload(self) -> None:
        with activated_tool_app("bridge-runtime"):
            writer = importlib.import_module("app.redis_stream_writer")
            received_at = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
            first_received_at = datetime(2026, 6, 8, 11, 59, 59, 500000, tzinfo=timezone.utc)
            payload = writer.build_stream_entry(
                payload=b"\x01\x02\x03",
                received_at=received_at,
                device_id="EE:01",
                source_name="windows_host_bridge",
                payload_encoding="hex",
                first_received_at=first_received_at,
                packet_count=4,
            )
            self.assertEqual(payload["device_id"], "EE:01")
            self.assertEqual(
                payload,
                {
                    "ts": "1780920000000",
                    "received_at": "2026-06-08T12:00:00Z",
                    "source": "windows_host_bridge",
                    "packet_count": "4",
                    "first_received_at": "2026-06-08T11:59:59.500000Z",
                    "device_id": "EE:01",
                    "payload_hex": "010203",
                },
            )

    def test_build_stream_entry_with_base64_payload(self) -> None:
        with activated_tool_app("bridge-runtime"):
            writer = importlib.import_module("app.redis_stream_writer")
            received_at = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
            payload = writer.build_stream_entry(
                payload=b"\x01\x02\x03",
                received_at=received_at,
                device_id=None,
                source_name="windows_host_bridge",
                payload_encoding="base64",
            )
            self.assertEqual(payload["payload_base64"], "AQID")
            self.assertNotIn("device_id", payload)

    def test_unknown_encoding_keeps_legacy_hex_fallback(self) -> None:
        with activated_tool_app("bridge-runtime"):
            writer = importlib.import_module("app.redis_stream_writer")
            payload = writer.build_stream_entry(
                payload=b"\xaa\x55",
                received_at=datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc),
                device_id=None,
                source_name="windows_host_bridge",
                payload_encoding="unexpected",
            )
            self.assertEqual(payload["payload_hex"], "aa55")
            self.assertNotIn("payload_base64", payload)


if __name__ == "__main__":
    unittest.main()
