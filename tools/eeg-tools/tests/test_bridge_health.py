from __future__ import annotations

import importlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.bootstrap import activated_tool_app


class BridgeHealthTests(unittest.TestCase):
    def test_health_store_writes_json_snapshot(self) -> None:
        with activated_tool_app("bridge-runtime"):
            health = importlib.import_module("app.health")
            with tempfile.TemporaryDirectory() as temp_dir:
                status_file = Path(temp_dir) / "status.json"
                store = health.BridgeHealthStore(status_file)
                store.update(status="streaming", device_id="EE:01", packet_count=3)
                store.write()

                payload = json.loads(status_file.read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "streaming")
                self.assertEqual(payload["device_id"], "EE:01")
                self.assertEqual(payload["packet_count"], 3)

    def test_health_store_supports_concurrent_writes(self) -> None:
        with activated_tool_app("bridge-runtime"):
            health = importlib.import_module("app.health")
            with tempfile.TemporaryDirectory() as temp_dir:
                status_file = Path(temp_dir) / "status.json"
                store = health.BridgeHealthStore(status_file)
                errors: list[Exception] = []

                def _writer(worker_id: int) -> None:
                    try:
                        for index in range(10):
                            store.update(status="streaming", writer=worker_id, index=index)
                            store.write()
                    except Exception as exc:
                        errors.append(exc)

                threads = [
                    threading.Thread(target=_writer, args=(worker_id,))
                    for worker_id in range(4)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

                self.assertEqual(errors, [])
                payload = json.loads(status_file.read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "streaming")
                self.assertIn("writer", payload)
                self.assertIn("index", payload)


if __name__ == "__main__":
    unittest.main()
