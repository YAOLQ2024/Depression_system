"""Export the selected facial-expression ViT to ONNX."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
import torch
from torch import nn
from transformers import AutoModelForImageClassification


class FaceRuntimeContract(nn.Module):
    """Expose image-classification logits with stable runtime names."""

    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        """Return seven native facial-expression logits."""
        return self.model(pixel_values=input, return_dict=False)[0]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--seed", type=int, default=20261003)
    return parser.parse_args()


def tensor_metadata(items: list[Any]) -> list[dict[str, Any]]:
    """Convert ONNX Runtime tensor metadata to JSON-safe dictionaries."""
    return [
        {"name": item.name, "type": item.type, "shape": item.shape}
        for item in items
    ]


def main() -> None:
    """Export the model and validate PyTorch/ONNX numerical parity."""
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    model_dir = args.model_dir.resolve()
    output_path = args.output.resolve()
    report_path = args.report.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    base_model = AutoModelForImageClassification.from_pretrained(
        model_dir,
        local_files_only=True,
    ).eval()
    model = FaceRuntimeContract(base_model).eval()
    rng = np.random.default_rng(args.seed)
    array = rng.normal(0.0, 0.5, size=(1, 3, 224, 224)).astype(np.float32)
    example = torch.from_numpy(array)

    with torch.no_grad():
        torch.onnx.export(
            model,
            (example,),
            str(output_path),
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=args.opset,
            do_constant_folding=True,
        )

    onnx.checker.check_model(str(output_path))
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        torch_logits = model(example).cpu().numpy()
    ort_logits = session.run(["output"], {"input": array})[0]
    max_abs_error = float(np.max(np.abs(torch_logits - ort_logits)))
    report = {
        "artifact": str(output_path),
        "source_model_dir": str(model_dir),
        "opset": args.opset,
        "id2label": {str(k): str(v) for k, v in base_model.config.id2label.items()},
        "inputs": tensor_metadata(session.get_inputs()),
        "outputs": tensor_metadata(session.get_outputs()),
        "validation": {
            "max_abs_error": max_abs_error,
            "argmax_torch": int(np.argmax(torch_logits[0])),
            "argmax_onnx": int(np.argmax(ort_logits[0])),
            "passed": max_abs_error <= 1e-4
            and int(np.argmax(torch_logits[0])) == int(np.argmax(ort_logits[0])),
        },
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not report["validation"]["passed"]:
        raise RuntimeError(f"ONNX parity validation failed; see {report_path}")


if __name__ == "__main__":
    main()
