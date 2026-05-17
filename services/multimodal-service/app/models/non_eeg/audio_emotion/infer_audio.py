import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import onnxruntime as ort
from transformers import AutoFeatureExtractor

MODEL_SAMPLE_RATE = 16000


LABEL_MAP = {
    "ang": "angry",
    "hap": "happy",
    "neu": "neutral",
    "sad": "sad",
    "angry": "angry",
    "happy": "happy",
    "neutral": "neutral",
}


@dataclass
class AudioRuntimeEngine:
    feature_extractor: object
    session: ort.InferenceSession
    id2label: Dict[int, str]


def resolve_providers(providers: Optional[Sequence[str]] = None):
    if providers:
        return list(providers)
    return ["CPUExecutionProvider"]


def to_readable_label(raw: str) -> str:
    return LABEL_MAP.get(str(raw).strip().lower(), str(raw).strip().lower())


def build_runtime_engine(model_dir: str = "", model_path: str = "", providers: Optional[Sequence[str]] = None) -> AudioRuntimeEngine:
    base_dir = Path(model_dir).expanduser().resolve() if model_dir else Path(__file__).resolve().parent
    onnx_path = Path(model_path).expanduser().resolve() if model_path else (base_dir / "model.onnx")
    feature_extractor = AutoFeatureExtractor.from_pretrained(str(base_dir / "preprocessor"))
    session = ort.InferenceSession(str(onnx_path), providers=resolve_providers(providers))
    raw = json.loads((base_dir / "labels.json").read_text(encoding="utf-8"))
    id2label = {int(k): str(v) for k, v in raw.items()}
    return AudioRuntimeEngine(feature_extractor=feature_extractor, session=session, id2label=id2label)


def rms_energy(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x))))


def resample_linear(x: np.ndarray, in_sr: int, out_sr: int) -> np.ndarray:
    if in_sr == out_sr:
        return x.astype(np.float32, copy=False)
    if x.size == 0:
        return x.astype(np.float32)
    out_len = max(1, int(round(x.size * out_sr / in_sr)))
    old_pos = np.linspace(0.0, 1.0, num=x.size, dtype=np.float64)
    new_pos = np.linspace(0.0, 1.0, num=out_len, dtype=np.float64)
    y = np.interp(new_pos, old_pos, x.astype(np.float64, copy=False))
    return y.astype(np.float32)


def predict_audio(engine: AudioRuntimeEngine, audio_16k: np.ndarray, top_k: int = 4) -> Dict:
    inputs = engine.feature_extractor(
        audio_16k,
        sampling_rate=MODEL_SAMPLE_RATE,
        return_tensors="np",
    )
    logits = engine.session.run(None, {"input_values": inputs["input_values"]})[0][0]
    probs = np.exp(logits - np.max(logits))
    probs = probs / np.sum(probs)
    order = np.argsort(-probs)
    topk: List[Tuple[str, float]] = []
    for idx in order[:top_k]:
        topk.append((to_readable_label(engine.id2label[int(idx)]), float(probs[int(idx)])))
    best_idx = int(order[0])
    return {
        "modality": "audio",
        "label": to_readable_label(engine.id2label[best_idx]),
        "score": float(probs[best_idx]),
        "extra": {"topk": topk},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
