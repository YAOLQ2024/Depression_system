import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np
import onnxruntime as ort


STANDARD_LABELS = ["angry", "disgust", "fear", "happy", "sad", "surprised", "neutral"]
RAW_TO_STANDARD = {
    "angry": "angry",
    "disgust": "disgust",
    "fear": "fear",
    "happy": "happy",
    "sad": "sad",
    "surprise": "surprised",
    "surprised": "surprised",
    "neutral": "neutral",
}
LABEL_ZH = {
    "angry": "愤怒",
    "disgust": "厌恶",
    "fear": "恐惧",
    "happy": "高兴",
    "sad": "悲伤",
    "surprised": "惊讶",
    "neutral": "中性",
}


@dataclass
class FaceRuntimeEngine:
    session: ort.InferenceSession
    input_name: str
    output_name: str
    detector: object
    prev_center: Optional[Tuple[float, float]] = None


def resolve_providers(providers: Optional[Sequence[str]] = None):
    if providers:
        return list(providers)
    return ["CPUExecutionProvider"]


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    ex = np.exp(x)
    return ex / np.sum(ex)


def preprocess_gray_face(face_gray: np.ndarray) -> np.ndarray:
    face = cv2.resize(face_gray, (48, 48), interpolation=cv2.INTER_LINEAR)
    face = face.astype(np.float32) / 255.0
    face = np.expand_dims(face, axis=0)
    face = (face - 0.5) / 0.5
    face = np.expand_dims(face, axis=0)
    return face.astype(np.float32)


def choose_primary_face(faces, prev_center: Optional[Tuple[float, float]]):
    if len(faces) == 0:
        return None
    if prev_center is None:
        return max(faces, key=lambda f: f[2] * f[3])
    px, py = prev_center

    def score(face):
        x, y, w, h = face
        cx = x + 0.5 * w
        cy = y + 0.5 * h
        dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
        return -dist + 0.05 * (w * h) ** 0.5

    return max(faces, key=score)


def normalize_label(raw_label: str) -> str:
    return RAW_TO_STANDARD.get(str(raw_label).strip().lower(), str(raw_label).strip().lower())


def build_scores(probs: np.ndarray, raw_labels) -> dict:
    mapped = {}
    for idx, raw in enumerate(raw_labels):
        mapped[normalize_label(raw)] = float(probs[idx])
    scores = {}
    for label in STANDARD_LABELS:
        scores[label] = float(mapped.get(label, 0.0))
    return scores


def build_ok_result(scores: dict, raw_emotion: str, latency_ms: Optional[float] = None, faces_detected: Optional[int] = None):
    dominant_emotion = max(scores, key=scores.get)
    result = {
        "status": "ok",
        "modality": "face",
        "dominant_emotion": dominant_emotion,
        "dominant_emotion_zh": LABEL_ZH[dominant_emotion],
        "confidence": float(scores[dominant_emotion]),
        "scores": scores,
    }
    extra = {}
    if latency_ms is not None:
        extra["latency_ms"] = float(latency_ms)
    if raw_emotion:
        extra["raw_emotion"] = raw_emotion
    if faces_detected is not None:
        extra["faces_detected"] = int(faces_detected)
    if extra:
        result["extra"] = extra
    return result


def build_no_face_result():
    return {
        "status": "no_face",
        "modality": "face",
        "dominant_emotion": "neutral",
        "dominant_emotion_zh": LABEL_ZH["neutral"],
        "confidence": 0.0,
        "scores": {},
    }


def build_runtime_engine(model_path: str = "", providers: Optional[Sequence[str]] = None) -> FaceRuntimeEngine:
    base_dir = Path(__file__).resolve().parent
    onnx_path = Path(model_path).expanduser().resolve() if model_path else (base_dir / "model.onnx")
    session = ort.InferenceSession(str(onnx_path), providers=resolve_providers(providers))
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if detector.empty():
        raise RuntimeError("Cannot load haarcascade_frontalface_default.xml")
    return FaceRuntimeEngine(
        session=session,
        input_name=session.get_inputs()[0].name,
        output_name=session.get_outputs()[0].name,
        detector=detector,
    )


def infer_image(engine: FaceRuntimeEngine, frame: np.ndarray):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = engine.detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    face = choose_primary_face(faces, engine.prev_center)
    if face is None:
        return build_no_face_result()

    x, y, w, h = face
    engine.prev_center = (x + 0.5 * w, y + 0.5 * h)
    pad = 10
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(gray.shape[1], x + w + pad)
    y2 = min(gray.shape[0], y + h + pad)
    roi = gray[y1:y2, x1:x2]
    if roi.size == 0:
        return {
            "status": "error",
            "modality": "face",
            "dominant_emotion": "neutral",
            "dominant_emotion_zh": LABEL_ZH["neutral"],
            "confidence": 0.0,
            "scores": {},
        }

    model_input = preprocess_gray_face(roi)
    t0 = time.perf_counter()
    logits = engine.session.run([engine.output_name], {engine.input_name: model_input})[0][0]
    latency_ms = (time.perf_counter() - t0) * 1000.0
    probs = softmax(logits)

    raw_labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
    raw_emotion = raw_labels[int(np.argmax(probs))]
    scores = build_scores(probs, raw_labels)
    return build_ok_result(scores, raw_emotion=raw_emotion, latency_ms=latency_ms, faces_detected=len(faces))


def predict_frame(engine: FaceRuntimeEngine, frame: np.ndarray):
    result = infer_image(engine, frame)
    return result
