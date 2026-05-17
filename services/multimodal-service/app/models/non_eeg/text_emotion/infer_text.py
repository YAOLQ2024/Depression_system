import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


@dataclass
class TextRuntimeEngine:
    tokenizer: object
    session: ort.InferenceSession
    id2label: Dict[int, str]


def resolve_providers(providers: Optional[Sequence[str]] = None):
    if providers:
        return list(providers)
    return ["CPUExecutionProvider"]


def normalize_label(label: str) -> str:
    s = str(label).strip().lower()
    if s in {"label_1", "positive", "pos"}:
        return "positive"
    if s in {"label_0", "negative", "neg"}:
        return "negative"
    return s


def build_runtime_engine(model_dir: str = "", model_path: str = "", providers: Optional[Sequence[str]] = None) -> TextRuntimeEngine:
    base_dir = Path(model_dir).expanduser().resolve() if model_dir else Path(__file__).resolve().parent
    onnx_path = Path(model_path).expanduser().resolve() if model_path else (base_dir / "model.onnx")
    tokenizer = AutoTokenizer.from_pretrained(str(base_dir / "tokenizer"))
    session = ort.InferenceSession(str(onnx_path), providers=resolve_providers(providers))

    labels_path = base_dir / "labels.json"
    id2label = {}
    if labels_path.exists():
        import json

        raw = json.loads(labels_path.read_text(encoding="utf-8"))
        id2label = {int(k): str(v) for k, v in raw.items()}
    return TextRuntimeEngine(tokenizer=tokenizer, session=session, id2label=id2label)


def predict_text(engine: TextRuntimeEngine, text: str) -> Dict:
    encoded = engine.tokenizer(text, return_tensors="np", truncation=True, max_length=256)
    input_ids = encoded["input_ids"].astype(np.int64, copy=False)
    attention_mask = encoded["attention_mask"].astype(np.int64, copy=False)
    outputs = engine.session.run(["logits"], {"input_ids": input_ids, "attention_mask": attention_mask})[0]
    probs = np.exp(outputs[0] - np.max(outputs[0]))
    probs = probs / np.sum(probs)
    order = np.argsort(-probs)
    idx = int(np.argmax(probs))
    raw_label = engine.id2label.get(idx, f"LABEL_{idx}")
    topk = []
    for top_idx in order[:3]:
        label = engine.id2label.get(int(top_idx), f"LABEL_{int(top_idx)}")
        topk.append((normalize_label(label), float(probs[int(top_idx)])))
    return {
        "modality": "text",
        "label": normalize_label(raw_label),
        "score": float(probs[idx]),
        "extra": {
            "text": text,
            "topk": topk,
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
