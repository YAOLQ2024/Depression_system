from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eeg_tools.main import _bridge_argv, _replay_argv, build_arg_parser


class CliTests(unittest.TestCase):
    def test_bridge_print_config_translation(self) -> None:
        args = build_arg_parser().parse_args(["bridge", "--print-config"])
        self.assertEqual(_bridge_argv(args), ["--print-config"])

    def test_replay_raw_translation(self) -> None:
        args = build_arg_parser().parse_args(
            [
                "replay",
                "raw",
                "--file",
                "sample.jsonl",
                "--speed",
                "8",
                "--loop",
                "--max-records",
                "10",
            ]
        )
        argv = _replay_argv(args)
        self.assertIn("--mode", argv)
        self.assertIn("raw", argv)
        self.assertIn("--file", argv)
        self.assertIn("--speed", argv)
        self.assertIn("--loop", argv)
        self.assertIn("--max-records", argv)

    def test_replay_simulate_translation(self) -> None:
        args = build_arg_parser().parse_args(
            [
                "replay",
                "simulate",
                "--duration-seconds",
                "30",
                "--speed",
                "2",
                "--print-config",
            ]
        )
        argv = _replay_argv(args)
        self.assertEqual(argv[0:2], ["--mode", "simulate"])
        self.assertIn("--duration-seconds", argv)
        self.assertIn("--print-config", argv)


if __name__ == "__main__":
    unittest.main()
