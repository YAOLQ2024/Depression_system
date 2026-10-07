"""Export the selected AGCN checkpoint to the depression-system ONNX contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
import torch
from torch import nn


class PoseRuntimeContract(nn.Module):
    """Adapt system sequence layout to AGCN and return normalized probabilities."""

    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        """Run AGCN from a ``[B, T, 21, 4]`` system input.

        Args:
            sequence: Batched pose sequence in the depression-system layout.

        Returns:
            Four-class probabilities ordered as ang, sad, neu, hap.
        """
        agcn_input = sequence.permute(0, 3, 1, 2).unsqueeze(-1)
        logits = self.model(agcn_input)
        return torch.softmax(logits, dim=1)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--model-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--seed", type=int, default=20261003)
    return parser.parse_args()


def load_source_module(path: Path) -> ModuleType:
    """Load the frozen AGCN source module.

    Args:
        path: Path to the copied training/model source.

    Returns:
        Imported module containing AGCNEmotion and adjacency helpers.
    """
    spec = importlib.util.spec_from_file_location("agcn_model_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import AGCN model source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_model(module: ModuleType, checkpoint: dict[str, Any]) -> PoseRuntimeContract:
    """Reconstruct the selected AGCN model from checkpoint metadata."""
    label2id = {str(k): int(v) for k, v in checkpoint["label2id"].items()}
    num_joints = int(checkpoint["num_joints"])
    in_channels = int(checkpoint["in_channels"])
    edges = [(int(a), int(b)) for a, b in checkpoint["edges"]]
    adjacency = module.build_agcn_adjacency(num_joints, edges)
    model = module.AGCNEmotion(
        in_channels=in_channels,
        num_classes=len(label2id),
        num_joints=num_joints,
        adjacency=adjacency,
    )
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.eval()
    return PoseRuntimeContract(model).eval()


def validate_contract(
    model: PoseRuntimeContract,
    output_path: Path,
    seed: int,
) -> dict[str, Any]:
    """Compare PyTorch and ONNX Runtime on formal and short windows."""
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(seed)
    cases: list[dict[str, Any]] = []
    for frames in (96, 8):
        array = rng.normal(0.0, 0.25, size=(1, frames, 21, 4)).astype(np.float32)
        with torch.no_grad():
            torch_probs = model(torch.from_numpy(array)).cpu().numpy()
        ort_probs = session.run(["probs"], {"sequence": array})[0]
        max_abs_error = float(np.max(np.abs(torch_probs - ort_probs)))
        prob_sum_error = float(np.max(np.abs(np.sum(ort_probs, axis=1) - 1.0)))
        cases.append(
            {
                "frames": frames,
                "shape": list(ort_probs.shape),
                "max_abs_error": max_abs_error,
                "probability_sum_error": prob_sum_error,
                "passed": max_abs_error <= 1e-4 and prob_sum_error <= 1e-5,
            }
        )
    inputs = [
        {"name": item.name, "type": item.type, "shape": item.shape}
        for item in session.get_inputs()
    ]
    outputs = [
        {"name": item.name, "type": item.type, "shape": item.shape}
        for item in session.get_outputs()
    ]
    return {
        "inputs": inputs,
        "outputs": outputs,
        "providers": session.get_providers(),
        "cases": cases,
        "passed": all(case["passed"] for case in cases),
    }


def main() -> None:
    """Export and validate the pose model."""
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    checkpoint_path = args.checkpoint.resolve()
    source_path = args.model_source.resolve()
    output_path = args.output.resolve()
    report_path = args.report.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    module = load_source_module(source_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = build_model(module, checkpoint)
    seq_len = int(checkpoint["seq_len"])
    example = torch.zeros((1, seq_len, 21, 4), dtype=torch.float32)

    with torch.no_grad():
        torch.onnx.export(
            model,
            (example,),
            str(output_path),
            input_names=["sequence"],
            output_names=["probs"],
            dynamic_axes={
                "sequence": {0: "batch", 1: "time"},
                "probs": {0: "batch"},
            },
            opset_version=args.opset,
            do_constant_folding=True,
        )

    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)
    validation = validate_contract(model, output_path, args.seed)
    report = {
        "artifact": str(output_path),
        "source_checkpoint": str(checkpoint_path),
        "source_model_code": str(source_path),
        "opset": args.opset,
        "label2id": checkpoint["label2id"],
        "training_contract": {
            "seq_len": seq_len,
            "num_joints": int(checkpoint["num_joints"]),
            "in_channels": int(checkpoint["in_channels"]),
        },
        "runtime_contract": {
            "layout": "[batch, time, 21, 4]",
            "output": "four-class probabilities",
            "dynamic_time": True,
        },
        "validation": validation,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not validation["passed"]:
        raise RuntimeError(f"ONNX parity validation failed; see {report_path}")


if __name__ == "__main__":
    main()
