#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

MODEL_PRESETS = {
    "base.cn": {
        "repo_id": "DataoceanAI1/dolphin-cn-dialect-base",
        "files": (
            "base.cn.pt",
            "train.yaml",
            "units.txt",
            "global_cmvn",
        ),
    },
    "base.cn.streaming": {
        "repo_id": "DataoceanAI1/dolphin-cn-dialect-base-streaming",
        "files": (
            "base.cn.streaming.pt",
            "train.yaml",
            "units.txt",
            "global_cmvn",
        ),
    },
    "small.cn.streaming": {
        "repo_id": "DataoceanAI1/dolphin-cn-dialect-small-streaming",
        "files": (
            "small.cn.streaming.pt",
            "train.yaml",
            "units.txt",
            "global_cmvn",
        ),
    },
}


def resolve_model_name() -> str:
    return os.environ.get("DOLPHIN_MODEL_NAME", "base.cn.streaming").strip() or "base.cn.streaming"


def resolve_target_dir(model_name: str) -> Path:
    default_dir = Path("/app/runtime-assets/asr") / model_name
    configured = Path(os.environ.get("DOLPHIN_MODEL_DIR", str(default_dir)))
    return configured.expanduser().resolve()


def resolve_model_repo_id(model_name: str) -> str:
    configured = os.environ.get("DOLPHIN_MODEL_REPO_ID", "").strip()
    if configured:
        return configured

    preset = MODEL_PRESETS.get(model_name)
    if preset:
        return str(preset["repo_id"])

    raise ValueError(
        f"Unsupported Dolphin model '{model_name}'. Set DOLPHIN_MODEL_REPO_ID explicitly."
    )


def resolve_required_files(model_name: str) -> tuple[str, ...]:
    configured = os.environ.get("DOLPHIN_MODEL_REQUIRED_FILES", "").strip()
    if configured:
        parts = [part.strip() for part in configured.split(",") if part.strip()]
        if parts:
            return tuple(parts)

    preset = MODEL_PRESETS.get(model_name)
    if preset:
        return tuple(str(filename) for filename in preset["files"])

    raise ValueError(
        f"Unsupported Dolphin model '{model_name}'. Set DOLPHIN_MODEL_REQUIRED_FILES explicitly."
    )


def main() -> int:
    model_name = resolve_model_name()
    target_dir = resolve_target_dir(model_name)
    repo_id = resolve_model_repo_id(model_name)
    required_files = resolve_required_files(model_name)

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Installing Dolphin model '{model_name}' to {target_dir}")
    for filename in required_files:
        target_path = target_dir / filename
        if target_path.is_file():
            print(f"[OK]   Keeping existing file: {filename}")
            continue

        print(f"[INFO] Downloading {filename} from {repo_id}")
        cached_path = Path(
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                repo_type="model",
            )
        )
        shutil.copy2(cached_path, target_path)
        print(f"[OK]   Installed {filename} ({target_path.stat().st_size} bytes)")

    missing = [filename for filename in required_files if not (target_dir / filename).is_file()]
    if missing:
        print("[FAIL] Missing required Dolphin assets after download: " + ", ".join(missing))
        return 1

    print(f"[OK]   Dolphin model '{model_name}' runtime assets are ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
