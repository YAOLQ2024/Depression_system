from __future__ import annotations

import argparse
from pathlib import Path

from eeg_tools import _frozen_imports as _  # noqa: F401
from eeg_tools.bootstrap import load_tool_main


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eeg-tools",
        description="Unified Windows EEG tool entry for bridge and replay workflows",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bridge_parser = subparsers.add_parser("bridge", help="run the host EEG bridge")
    bridge_parser.add_argument("--print-config", action="store_true", help="print resolved bridge config and exit")

    replay_parser = subparsers.add_parser("replay", help="run EEG replay workflows")
    replay_subparsers = replay_parser.add_subparsers(dest="replay_mode", required=True)

    raw_parser = replay_subparsers.add_parser("raw", help="replay a recorded jsonl file")
    raw_parser.add_argument("--file", dest="replay_file", help="recorded jsonl file path")
    raw_parser.add_argument("--speed", type=float, help="timing multiplier, e.g. 8.0 means 8x faster")
    raw_parser.add_argument("--loop", action="store_true", help="loop the raw replay file")
    raw_parser.add_argument("--max-records", type=int, help="stop after this many published entries")
    raw_parser.add_argument("--print-config", action="store_true", help="print resolved replay config and exit")

    simulate_parser = replay_subparsers.add_parser("simulate", help="generate simulated EEG traffic")
    simulate_parser.add_argument("--duration-seconds", type=float, help="simulate mode duration")
    simulate_parser.add_argument("--speed", type=float, help="timing multiplier, e.g. 8.0 means 8x faster")
    simulate_parser.add_argument("--print-config", action="store_true", help="print resolved replay config and exit")

    return parser


def _bridge_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.print_config:
        argv.append("--print-config")
    return argv


def _replay_argv(args: argparse.Namespace) -> list[str]:
    argv = ["--mode", str(args.replay_mode)]
    if getattr(args, "replay_file", None):
        argv.extend(["--file", str(Path(args.replay_file).resolve())])
    if getattr(args, "speed", None) is not None:
        argv.extend(["--speed", str(float(args.speed))])
    if getattr(args, "loop", False):
        argv.append("--loop")
    if getattr(args, "max_records", None) is not None:
        argv.extend(["--max-records", str(int(args.max_records))])
    if getattr(args, "duration_seconds", None) is not None:
        argv.extend(["--duration-seconds", str(float(args.duration_seconds))])
    if getattr(args, "print_config", False):
        argv.append("--print-config")
    return argv


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.command == "bridge":
        bridge_main = load_tool_main("bridge-runtime")
        return int(bridge_main(_bridge_argv(args)))
    if args.command == "replay":
        replay_main = load_tool_main("replay-runtime")
        return int(replay_main(_replay_argv(args)))
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
