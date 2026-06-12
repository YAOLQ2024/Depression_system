from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.bridge_worker import EegHostBridgeWorker
from app.config import get_settings


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
    parser = argparse.ArgumentParser(description="Windows EEG BLE to Redis Stream bridge")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="print resolved bridge config and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    settings = get_settings()
    _configure_logging(str(settings["log_level"]))

    if args.print_config:
        print(json.dumps(_serialize_settings(settings), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    worker = EegHostBridgeWorker(settings=settings)
    worker.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
