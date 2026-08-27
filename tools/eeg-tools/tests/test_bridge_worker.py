from __future__ import annotations

import importlib
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class BridgeWorkerProtocolTests(unittest.TestCase):
    def test_batch_payload_is_exact_notification_concatenation(self) -> None:
        with activated_tool_app("bridge-runtime"):
            bridge_worker = importlib.import_module("app.bridge_worker")
            received_at = datetime(2026, 8, 26, 8, 0, 0, tzinfo=timezone.utc)
            batch = [
                bridge_worker.PacketEnvelope(b"\xaa\x55\x01", "EE:01", received_at),
                bridge_worker.PacketEnvelope(b"\x02\x03", "EE:01", received_at),
                bridge_worker.PacketEnvelope(b"\x04\x0d\x0a", "EE:01", received_at),
            ]

            self.assertEqual(
                bridge_worker.combine_packet_payloads(batch),
                b"\xaa\x55\x01\x02\x03\x04\x0d\x0a",
            )


if __name__ == "__main__":
    unittest.main()
