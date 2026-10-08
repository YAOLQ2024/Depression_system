#!/usr/bin/env python3
"""Build board-specific TensorRT engines without replacing the original model files."""
from __future__ import annotations

import json
import argparse
import hashlib
from pathlib import Path
import subprocess


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assets = root / "services/multimodal-service/runtime-assets/models"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=root / ".codex-tmp/tensorrt-upgrade-20261007")
    parser.add_argument("--modalities", nargs="+", choices=["face_emotion", "pose_emotion", "text_emotion", "audio_emotion"])
    args = parser.parse_args()
    output = args.output_dir.resolve()
    profiles = {
        "face_emotion": ["--minShapes=input:1x3x224x224", "--optShapes=input:1x3x224x224", "--maxShapes=input:1x3x224x224"],
        "pose_emotion": ["--minShapes=sequence:1x8x21x4", "--optShapes=sequence:1x96x21x4", "--maxShapes=sequence:1x96x21x4"],
        "text_emotion": ["--minShapes=input_ids:1x2,attention_mask:1x2", "--optShapes=input_ids:1x32,attention_mask:1x32", "--maxShapes=input_ids:1x256,attention_mask:1x256"],
        "audio_emotion": ["--minShapes=input_values:1x8000", "--optShapes=input_values:1x64000", "--maxShapes=input_values:1x160000"],
    }
    for modality, shape_args in profiles.items():
        if args.modalities and modality not in args.modalities:
            continue
        folder = output / modality
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / "model.building.plan"
        target = folder / "model.plan"
        command = [
            "/usr/src/tensorrt/bin/trtexec", f"--onnx={assets / modality / 'model.onnx'}",
            f"--saveEngine={temporary}", "--memPoolSize=workspace:256",
            "--builderOptimizationLevel=2", "--avgTiming=2", "--skipInference",
            f"--timingCacheFile={folder / 'timing.cache'}", *shape_args,
        ]
        # The upgraded pose graph overflows in FP16 for the 96-frame contract.
        command += ["--noTF32"] if modality == "pose_emotion" else ["--fp16"]
        print(f"Building {modality} (TensorRT engines are specific to this board)", flush=True)
        with (folder / "build.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        temporary.replace(target)
        (folder / "build-command.json").write_text(json.dumps(command, indent=2) + "\n")
        def digest(path: Path) -> str:
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        (folder / "manifest.json").write_text(json.dumps({
            "onnx_sha256": digest(assets / modality / "model.onnx"),
            "plan_sha256": digest(target),
            "board_release": Path("/etc/nv_tegra_release").read_text().strip(),
            "command": command,
        }, indent=2) + "\n")
        print(f"Built {modality}: {target.stat().st_size / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
