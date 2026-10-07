"""Verify the retained-Text plus upgraded Audio/Face/Pose deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
TARGET_MODEL_ROOT = (
    REPO_ROOT / "services" / "multimodal-service" / "runtime-assets" / "models"
)

BUNDLE_EXPECTED = {
    "audio/model.onnx": "250D51BBB75E5EF8B64E15D69B18D864B5DDCDFD67C275112147608C329A3C7B",
    "face/model.onnx": "6C9D4A184F1C3C8B545D3C106426401E9CC2034DAB13F98B6E04F4A541AE2094",
    "pose/model.onnx": "4CAF9BF2C84D22DE39EE4462033A54586DD93642A87C74DECC9E7BB285A484FC",
    "pose/source_best_model_seed72.pt": "5ABB1E24D1A2786776228E9998DE2187D3870E49F1602B268DF4CBE68A83E151",
}
TARGET_EXPECTED = {
    "text_emotion/model.onnx": "79D059FB850B17118D443B988C533E26FFB59291C8A8C358E461BC8FB9C559D9",
    "audio_emotion/model.onnx": "250D51BBB75E5EF8B64E15D69B18D864B5DDCDFD67C275112147608C329A3C7B",
    "face_emotion/model.onnx": "6C9D4A184F1C3C8B545D3C106426401E9CC2034DAB13F98B6E04F4A541AE2094",
    "pose_emotion/model.onnx": "4CAF9BF2C84D22DE39EE4462033A54586DD93642A87C74DECC9E7BB285A484FC",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    """Calculate a file SHA256 using bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_hashes(root: Path, expected: dict[str, str]) -> dict[str, Any]:
    """Verify a group of files rooted at the selected directory."""
    result: dict[str, Any] = {}
    for relative, expected_hash in expected.items():
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        result[relative] = {
            "expected": expected_hash,
            "actual": actual,
            "passed": actual == expected_hash,
        }
    return result


def session(path: Path) -> ort.InferenceSession:
    """Create a deterministic CPU inference session."""
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def metadata(items: list[Any]) -> list[dict[str, Any]]:
    """Convert ONNX Runtime tensor metadata to serializable dictionaries."""
    return [
        {"name": item.name, "type": item.type, "shape": item.shape}
        for item in items
    ]


def verify_inference() -> dict[str, Any]:
    """Run minimal contract checks against the installed target models."""
    inference: dict[str, Any] = {}

    text = session(TARGET_MODEL_ROOT / "text_emotion" / "model.onnx")
    ids = np.array([[0, 10, 20, 2]], dtype=np.int64)
    text_out = text.run(
        ["logits"],
        {"input_ids": ids, "attention_mask": np.ones_like(ids)},
    )[0]
    inference["text"] = {
        "selection": "retained_existing",
        "inputs": metadata(text.get_inputs()),
        "outputs": metadata(text.get_outputs()),
        "result_shape": list(text_out.shape),
        "passed": list(text_out.shape) == [1, 2],
    }
    del text

    audio = session(TARGET_MODEL_ROOT / "audio_emotion" / "model.onnx")
    audio_cases = []
    for length in (8000, 16000, 32000):
        output = audio.run(
            ["logits"],
            {"input_values": np.zeros((1, length), dtype=np.float32)},
        )[0]
        audio_cases.append({"sample_count": length, "shape": list(output.shape)})
    inference["audio"] = {
        "selection": "upgraded",
        "inputs": metadata(audio.get_inputs()),
        "outputs": metadata(audio.get_outputs()),
        "cases": audio_cases,
        "passed": all(item["shape"] == [1, 9] for item in audio_cases),
    }
    del audio

    face = session(TARGET_MODEL_ROOT / "face_emotion" / "model.onnx")
    face_out = face.run(
        ["output"],
        {"input": np.zeros((1, 3, 224, 224), dtype=np.float32)},
    )[0]
    inference["face"] = {
        "selection": "upgraded",
        "inputs": metadata(face.get_inputs()),
        "outputs": metadata(face.get_outputs()),
        "result_shape": list(face_out.shape),
        "passed": list(face_out.shape) == [1, 7],
    }
    del face

    pose = session(TARGET_MODEL_ROOT / "pose_emotion" / "model.onnx")
    pose_cases = []
    for frames in (8, 96):
        output = pose.run(
            ["probs"],
            {"sequence": np.zeros((1, frames, 21, 4), dtype=np.float32)},
        )[0]
        pose_cases.append(
            {
                "frames": frames,
                "shape": list(output.shape),
                "probability_sum": float(output.sum(axis=1)[0]),
            }
        )
    inference["pose"] = {
        "selection": "upgraded",
        "inputs": metadata(pose.get_inputs()),
        "outputs": metadata(pose.get_outputs()),
        "cases": pose_cases,
        "passed": all(
            item["shape"] == [1, 4]
            and abs(item["probability_sum"] - 1.0) <= 1e-5
            for item in pose_cases
        ),
    }
    del pose
    return inference


def main() -> None:
    """Verify hashes, plans, graph contracts, and minimal inference."""
    args = parse_args()
    bundle_hashes = verify_hashes(ROOT, BUNDLE_EXPECTED)
    target_hashes = verify_hashes(TARGET_MODEL_ROOT, TARGET_EXPECTED)
    inference = verify_inference()
    plan_state = {
        modality: (TARGET_MODEL_ROOT / modality / "model.plan").is_file()
        for modality in (
            "text_emotion",
            "audio_emotion",
            "face_emotion",
            "pose_emotion",
        )
    }
    plans_passed = plan_state == {
        "text_emotion": True,
        "audio_emotion": False,
        "face_emotion": False,
        "pose_emotion": False,
    }
    passed = (
        all(item["passed"] for item in bundle_hashes.values())
        and all(item["passed"] for item in target_hashes.values())
        and all(item["passed"] for item in inference.values())
        and plans_passed
    )
    result = {
        "selection_profile": "legacy_text_plus_v4_audio_face_pose",
        "onnxruntime_version": ort.__version__,
        "bundle_hashes": bundle_hashes,
        "target_hashes": target_hashes,
        "inference": inference,
        "tensor_rt_plans_present": plan_state,
        "tensor_rt_plan_state_passed": plans_passed,
        "passed": passed,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
