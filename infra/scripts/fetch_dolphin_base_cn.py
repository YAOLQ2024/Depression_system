#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET_DIR = ROOT / "services" / "multimodal-service" / "runtime-assets" / "asr" / "base.cn"
MODEL_REPO_ID = "DataoceanAI1/dolphin-cn-dialect-base"
REQUIRED_FILES = (
    "base.cn.pt",
    "train.yaml",
    "units.txt",
    "global_cmvn",
)
HF_HUB_VERSION = "0.35.3"


def print_info(message: str) -> None:
    print(f"[INFO] {message}")


def print_ok(message: str) -> None:
    print(f"[OK]   {message}")


def print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def run_command(args: list[str]) -> None:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return
    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    detail = stderr or stdout or "unknown error"
    raise RuntimeError(f"{' '.join(args)} -> {detail}")


def ensure_huggingface_hub() -> None:
    if importlib.util.find_spec("huggingface_hub") is not None:
        return

    print_info(
        f"Installing huggingface_hub=={HF_HUB_VERSION} for model download..."
    )
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--user",
            f"huggingface_hub=={HF_HUB_VERSION}",
        ]
    )


def load_hf_hub_download():
    ensure_huggingface_hub()
    module = importlib.import_module("huggingface_hub")
    return getattr(module, "hf_hub_download")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the official Dolphin base.cn model into the fixed "
            "multimodal-service runtime-assets directory."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite existing model files.",
    )
    return parser.parse_args()


def download_required_files(force: bool) -> None:
    hf_hub_download = load_hf_hub_download()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    print_info(f"Installing Dolphin base.cn to fixed path: {TARGET_DIR}")
    print_info(f"Source model repo: {MODEL_REPO_ID}")

    for filename in REQUIRED_FILES:
        target_path = TARGET_DIR / filename
        if target_path.exists() and not force:
            print_ok(f"Keeping existing file: {target_path.name}")
            continue

        cached_path = Path(
            hf_hub_download(
                repo_id=MODEL_REPO_ID,
                filename=filename,
                repo_type="model",
            )
        )
        shutil.copy2(cached_path, target_path)
        print_ok(
            f"Installed {target_path.name} ({target_path.stat().st_size} bytes)"
        )


def validate_installation() -> None:
    missing = [
        filename
        for filename in REQUIRED_FILES
        if not (TARGET_DIR / filename).is_file()
    ]
    if missing:
        raise RuntimeError(
            "missing required files after download: " + ", ".join(missing)
        )

    print_ok(f"Model installation directory is ready: {TARGET_DIR}")


def main() -> int:
    args = parse_args()

    try:
        download_required_files(force=args.force)
        validate_installation()
    except Exception as exc:  # noqa: BLE001
        print_fail(str(exc))
        return 1

    print("\nNext step:")
    print("  docker compose -f infra/compose/docker-compose.dev.yml up -d --build multimodal-service gateway-service consultation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
