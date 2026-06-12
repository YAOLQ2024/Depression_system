from __future__ import annotations

import sys

from eeg_tools import _frozen_imports as _  # noqa: F401
from eeg_tools.bootstrap import load_tool_main


def main(argv: list[str] | None = None) -> int:
    bridge_main = load_tool_main("bridge-runtime")
    return int(bridge_main(list(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())
