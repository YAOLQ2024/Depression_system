from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class FakeWriter:
    def __init__(self) -> None:
        self.stream_key = "mcs:eeg:transport:default"
        self.published: list[dict[str, object]] = []

    def publish(self, **kwargs):
        self.published.append(dict(kwargs))
        return f"{len(self.published)}-0"


class ReplayRuntimeTests(unittest.TestCase):
    def test_iter_jsonl_records_decodes_hex_payload(self) -> None:
        with activated_tool_app("replay-runtime"):
            replay = importlib.import_module("app.replay")
            with tempfile.TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir) / "sample.jsonl"
                path.write_text(
                    json.dumps(
                        {
                            "received_at": "2026-06-08T12:00:00Z",
                            "device_id": "EE:01",
                            "payload_hex": "010203",
                            "source": "windows_host_bridge",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                records = list(replay.iter_jsonl_records(path))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].payload, b"\x01\x02\x03")
            self.assertEqual(records[0].device_id, "EE:01")

    def test_compute_sleep_seconds_respects_speed(self) -> None:
        with activated_tool_app("replay-runtime"):
            replay = importlib.import_module("app.replay")
            previous_at = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
            current_at = datetime(2026, 6, 8, 12, 0, 2, tzinfo=timezone.utc)
            self.assertEqual(
                replay.compute_sleep_seconds(previous_at, current_at, respect_timing=True, speed=4.0),
                0.5,
            )

    def test_raw_replayer_publishes_current_timestamps(self) -> None:
        with activated_tool_app("replay-runtime"):
            replay = importlib.import_module("app.replay")
            with tempfile.TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir) / "sample.jsonl"
                path.write_text(
                    "\n".join(
                        [
                            json.dumps(
                                {
                                    "received_at": "2026-06-08T12:00:00Z",
                                    "device_id": "EE:01",
                                    "payload_hex": "010203",
                                    "source": "windows_host_bridge",
                                }
                            ),
                            json.dumps(
                                {
                                    "received_at": "2026-06-08T12:00:00.050000Z",
                                    "device_id": "EE:01",
                                    "payload_hex": "040506",
                                    "source": "windows_host_bridge",
                                }
                            ),
                        ]
                    ),
                    encoding="utf-8",
                )
                writer = FakeWriter()
                runner = replay.RawBytesReplayer(
                    replay_file=path,
                    writer=writer,
                    source_name="eeg_replay",
                    respect_timing=False,
                    speed=1.0,
                    loop=False,
                    max_records=0,
                    sleep_fn=lambda _: None,
                )
                summary = runner.run()
            self.assertEqual(summary.published_entries, 2)
            self.assertEqual(len(writer.published), 2)
            self.assertEqual(writer.published[0]["payload"], b"\x01\x02\x03")
            self.assertIn("recorded_received_at", writer.published[0]["extra_fields"])

    def test_build_simulated_payload_window_emits_wave_and_feature_packets(self) -> None:
        with activated_tool_app("replay-runtime"):
            replay = importlib.import_module("app.replay")
            state = replay.SimulationState()
            payload, packet_count, wave_count, feature_count = replay.build_simulated_payload_window(
                state,
                window_start=0.0,
                window_end=1.0,
                wave_rate_hz=10,
                feature_rate_hz=1,
                amplitude=20.0,
            )
            self.assertGreater(len(payload), 0)
            self.assertEqual(packet_count, wave_count + feature_count)
            self.assertGreater(wave_count, 0)
            self.assertGreater(feature_count, 0)


if __name__ == "__main__":
    unittest.main()
