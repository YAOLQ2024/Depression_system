#!/usr/bin/env python3
"""Reject GPU startup when engines do not match their ONNX sources."""
import hashlib
import json
from pathlib import Path


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    engines = root / ".codex-tmp/tensorrt-upgrade-20261007"
    models = root / "services/multimodal-service/runtime-assets/models"
    for name in ("text_emotion", "audio_emotion", "face_emotion", "pose_emotion"):
        folder = engines / name
        try:
            manifest = json.loads((folder / "manifest.json").read_text())
            if digest(models / name / "model.onnx") != manifest["onnx_sha256"]:
                raise ValueError("ONNX source changed")
            if digest(folder / "model.plan") != manifest["plan_sha256"]:
                raise ValueError("engine changed")
            if manifest["board_release"] != Path("/etc/nv_tegra_release").read_text().strip():
                raise ValueError("Jetson release changed")
        except (OSError, ValueError, KeyError) as exc:
            raise SystemExit(f"Refusing stale TensorRT engine {name}: {exc}. Rebuild locally, or use MCS_TENSORRT_ENABLED=false.")
    print("Verified four local TensorRT engines and ONNX hashes", flush=True)


if __name__ == "__main__":
    main()
