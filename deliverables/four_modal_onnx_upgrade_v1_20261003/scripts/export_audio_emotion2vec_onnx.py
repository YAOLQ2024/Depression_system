"""Export emotion2vec_plus_large to the depression-system audio contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
import torch
from funasr import AutoModel
from torch import nn


class AudioRuntimeContract(nn.Module):
    """Expose raw-waveform input and utterance-level emotion logits."""

    def __init__(self, model: nn.Module, normalize: bool) -> None:
        super().__init__()
        self.model = model
        self.normalize = normalize

    def forward(self, input_values: torch.Tensor) -> torch.Tensor:
        """Return native nine-class emotion2vec logits.

        The source inference code applies ``layer_norm`` to a single waveform.
        This equivalent expression keeps the audio length exportable as a
        dynamic axis.
        """
        source = input_values
        if self.normalize:
            mean = source.mean(dim=-1, keepdim=True)
            variance = (source - mean).pow(2).mean(dim=-1, keepdim=True)
            source = (source - mean) * torch.rsqrt(variance + 1e-5)
        features = self.model.extract_features(source, padding_mask=None)["x"]
        pooled = features.mean(dim=1)
        return self.model.proj(pooled)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--sample-count", type=int, default=16000)
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

    loaded = AutoModel(
        model=str(model_dir),
        disable_update=True,
        device="cpu",
    )
    base_model = loaded.model.eval()
    if base_model.proj is None:
        raise RuntimeError("The selected emotion2vec checkpoint has no classifier head")
    model = AudioRuntimeContract(
        base_model,
        normalize=bool(base_model.cfg.normalize),
    ).eval()
    rng = np.random.default_rng(args.seed)
    waveform = rng.normal(0.0, 0.02, size=(1, args.sample_count)).astype(np.float32)
    example = torch.from_numpy(waveform)

    with torch.no_grad():
        torch.onnx.export(
            model,
            (example,),
            str(output_path),
            input_names=["input_values"],
            output_names=["logits"],
            dynamic_axes={
                "input_values": {0: "batch", 1: "audio_len"},
                "logits": {0: "batch"},
            },
            opset_version=args.opset,
            do_constant_folding=True,
            external_data=True,
        )

    onnx.checker.check_model(str(output_path))
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    cases: list[dict[str, Any]] = []
    for sample_count in sorted({8000, args.sample_count, 32000}):
        case_waveform = rng.normal(
            0.0,
            0.02,
            size=(1, sample_count),
        ).astype(np.float32)
        with torch.no_grad():
            torch_logits = model(torch.from_numpy(case_waveform)).cpu().numpy()
        ort_logits = session.run(
            ["logits"],
            {"input_values": case_waveform},
        )[0]
        max_abs_error = float(np.max(np.abs(torch_logits - ort_logits)))
        cases.append(
            {
                "sample_count": sample_count,
                "max_abs_error": max_abs_error,
                "argmax_torch": int(np.argmax(torch_logits[0])),
                "argmax_onnx": int(np.argmax(ort_logits[0])),
                "passed": max_abs_error <= 1e-3
                and int(np.argmax(torch_logits[0])) == int(np.argmax(ort_logits[0])),
            }
        )
    report = {
        "artifact": str(output_path),
        "source_model_dir": str(model_dir),
        "opset": args.opset,
        "sample_rate_hz": 16000,
        "native_labels": (model_dir / "tokens.txt").read_text(encoding="utf-8").splitlines(),
        "normalize_waveform": bool(base_model.cfg.normalize),
        "inputs": tensor_metadata(session.get_inputs()),
        "outputs": tensor_metadata(session.get_outputs()),
        "validation": {"cases": cases, "passed": all(case["passed"] for case in cases)},
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not report["validation"]["passed"]:
        raise RuntimeError(f"ONNX parity validation failed; see {report_path}")


if __name__ == "__main__":
    main()
