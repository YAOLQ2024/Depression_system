from __future__ import annotations

import contextlib
import importlib
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterator


def resolve_repo_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def resolve_suite_root() -> Path:
    if getattr(sys, "frozen", False):
        return (resolve_bundle_root() / "tools" / "eeg-tools").resolve()
    return Path(__file__).resolve().parents[1]


def resolve_bundle_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    return resolve_repo_root()


def tool_root(tool_dir_name: str) -> Path:
    return (resolve_suite_root() / tool_dir_name).resolve()


@contextlib.contextmanager
def activated_tool_app(tool_dir_name: str) -> Iterator[None]:
    target_root = tool_root(tool_dir_name)
    previous_path = list(sys.path)
    previous_modules: dict[str, ModuleType] = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    os.environ["MCS_EEG_TOOLS_ROOT"] = str(resolve_repo_root())
    for name in list(previous_modules):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(target_root))
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(previous_modules)
        sys.path[:] = previous_path


def load_tool_main(tool_dir_name: str):
    with activated_tool_app(tool_dir_name):
        module = importlib.import_module("app.main")
        return getattr(module, "main")
