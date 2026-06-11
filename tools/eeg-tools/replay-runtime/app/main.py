from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.redis_stream_writer import RedisStreamWriter
from app.replay import RawBytesReplayer, SimulatedReplayer


def _serialize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in settings.items():
        serialized[key] = str(value) if isinstance(value, Path) else value
    return serialized


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay EEG transport payloads into Redis Stream")
    parser.add_argument("--print-config", action="store_true", help="print resolved replay config and exit")
    parser.add_argument("--mode", choices=("raw", "simulate"), help="override replay mode")
    parser.add_argument("--file", dest="replay_file", help="recorded jsonl file for raw replay")
    parser.add_argument("--speed", type=float, help="timing multiplier, e.g. 8.0 means 8x faster")
    parser.add_argument("--loop", action="store_true", help="loop raw replay file")
    parser.add_argument("--max-records", type=int, help="stop after this many published entries")
    parser.add_argument("--duration-seconds", type=float, help="simulate mode duration")
    return parser


def _apply_arg_overrides(settings: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    resolved = dict(settings)
    if args.mode:
        resolved["mode"] = args.mode
    if args.replay_file:
        resolved["replay_file"] = Path(args.replay_file).resolve()
    if args.speed is not None:
        resolved["speed"] = max(0.0001, float(args.speed))
    if args.loop:
        resolved["loop"] = True
    if args.max_records is not None:
        resolved["max_records"] = max(0, int(args.max_records))
    if args.duration_seconds is not None:
        resolved["sim_duration_seconds"] = max(0.001, float(args.duration_seconds))
    return resolved


def _build_writer(settings: dict[str, Any]) -> RedisStreamWriter:
    return RedisStreamWriter(
        redis_url=str(settings["redis_url"]),
        stream_key=str(settings["stream_key"]),
        source_name=str(settings["source_name"]),
        payload_encoding=str(settings["payload_encoding"]),
        maxlen=int(settings["redis_maxlen"]),
        approximate_maxlen=bool(settings["redis_approx_maxlen"]),
        connect_timeout_seconds=float(settings["redis_connect_timeout_seconds"]),
        socket_timeout_seconds=float(settings["redis_socket_timeout_seconds"]),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    settings = _apply_arg_overrides(get_settings(), args)
    _configure_logging(str(settings["log_level"]))

    if args.print_config:
        print(json.dumps(_serialize_settings(settings), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    writer = _build_writer(settings)
    try:
        mode = str(settings["mode"]).strip().lower()
        if mode == "raw":
            replay_file = settings.get("replay_file")
            if replay_file is None:
                raise SystemExit("raw replay requires EEG_REPLAY_FILE or --file")
            runner = RawBytesReplayer(
                replay_file=Path(replay_file),
                writer=writer,
                source_name=str(settings["source_name"]),
                respect_timing=bool(settings["respect_timing"]),
                speed=float(settings["speed"]),
                loop=bool(settings["loop"]),
                max_records=int(settings["max_records"]),
                source_filter=settings.get("source_filter"),
            )
        elif mode == "simulate":
            runner = SimulatedReplayer(
                writer=writer,
                source_name=str(settings["source_name"]),
                speed=float(settings["speed"]),
                duration_seconds=float(settings["sim_duration_seconds"]),
                wave_rate_hz=int(settings["sim_wave_rate_hz"]),
                feature_rate_hz=int(settings["sim_feature_rate_hz"]),
                publish_interval_ms=int(settings["sim_publish_interval_ms"]),
                amplitude=float(settings["sim_amplitude"]),
                device_id=str(settings["sim_device_id"]),
            )
        else:
            raise SystemExit(f"unsupported replay mode: {mode}")

        summary = runner.run()
        logging.getLogger(__name__).info("EEG replay completed summary=%s", summary.as_dict())
        return 0
    finally:
        writer.close()


if __name__ == "__main__":
    raise SystemExit(main())
