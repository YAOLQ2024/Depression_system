import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Optional, Sequence, Tuple

import cv2
import numpy as np
import onnxruntime as ort


@dataclass
class PoseRuntimeEngine:
    session: ort.InferenceSession
    labels: Dict[int, str]
    mp: object
    pose: object
    pose_window: int = 96


@dataclass
class PoseTurnState:
    pose_buffer: Deque[np.ndarray] = field(default_factory=lambda: deque(maxlen=96))
    last_used_at: float = field(default_factory=time.time)


def resolve_providers(providers: Optional[Sequence[str]] = None):
    if providers:
        return list(providers)
    return ["CPUExecutionProvider"]


SHARED21_NAMES = [
    "pelvis",
    "spine",
    "spine_upper",
    "neck",
    "head",
    "left_shoulder",
    "left_elbow",
    "left_wrist",
    "right_shoulder",
    "right_elbow",
    "right_wrist",
    "left_hip",
    "left_knee",
    "left_ankle",
    "right_hip",
    "right_knee",
    "right_ankle",
    "left_thumb",
    "left_index",
    "right_thumb",
    "right_index",
]


def build_pose_estimator() -> Tuple[object, object]:
    try:
        import mediapipe as mp
    except ImportError as e:
        raise RuntimeError("Please install mediapipe first: pip install mediapipe") from e

    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp, pose


def build_runtime_engine(model_path: str = "", pose_window: int = 96, providers: Optional[Sequence[str]] = None) -> PoseRuntimeEngine:
    base_dir = Path(__file__).resolve().parent
    onnx_path = Path(model_path).expanduser().resolve() if model_path else (base_dir / "model.onnx")
    session = ort.InferenceSession(str(onnx_path), providers=resolve_providers(providers))
    raw = json.loads((base_dir / "labels.json").read_text(encoding="utf-8-sig"))
    labels = {int(k): str(v) for k, v in raw.items()}
    mp, pose = build_pose_estimator()
    return PoseRuntimeEngine(
        session=session,
        labels=labels,
        mp=mp,
        pose=pose,
        pose_window=max(8, int(pose_window)),
    )


def build_turn_state(pose_window: int = 96) -> PoseTurnState:
    return PoseTurnState(pose_buffer=deque(maxlen=max(8, int(pose_window))))


def pose_result_to_array(result) -> Optional[np.ndarray]:
    if result.pose_landmarks is None:
        return None
    arr = np.zeros((33, 4), dtype=np.float32)
    for i, lm in enumerate(result.pose_landmarks.landmark):
        arr[i, 0] = float(lm.x)
        arr[i, 1] = float(lm.y)
        arr[i, 2] = float(lm.z)
        arr[i, 3] = float(getattr(lm, "visibility", 1.0))
    return arr


def midpoint(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a + b) * 0.5


def lerp(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    return a * (1.0 - alpha) + b * alpha


def adapt_mediapipe_33_to_shared21(seq: np.ndarray) -> np.ndarray:
    seq = np.asarray(seq, dtype=np.float32)
    if seq.ndim != 3 or seq.shape[1] != 33 or seq.shape[2] < 4:
        raise ValueError(f"Expected MediaPipe pose sequence [T, 33, 4], got {seq.shape}")
    out = np.zeros((seq.shape[0], len(SHARED21_NAMES), 4), dtype=np.float32)
    left_hip = seq[:, 23]
    right_hip = seq[:, 24]
    left_shoulder = seq[:, 11]
    right_shoulder = seq[:, 12]
    hip_mid = midpoint(left_hip, right_hip)
    shoulder_mid = midpoint(left_shoulder, right_shoulder)
    nose = seq[:, 0]

    out[:, 0] = hip_mid
    out[:, 1] = lerp(hip_mid, shoulder_mid, 0.35)
    out[:, 2] = shoulder_mid
    out[:, 3] = lerp(shoulder_mid, nose, 0.35)
    out[:, 4] = nose
    out[:, 5] = left_shoulder
    out[:, 6] = seq[:, 13]
    out[:, 7] = seq[:, 15]
    out[:, 8] = right_shoulder
    out[:, 9] = seq[:, 14]
    out[:, 10] = seq[:, 16]
    out[:, 11] = left_hip
    out[:, 12] = seq[:, 25]
    out[:, 13] = seq[:, 27]
    out[:, 14] = right_hip
    out[:, 15] = seq[:, 26]
    out[:, 16] = seq[:, 28]
    out[:, 17] = seq[:, 21]
    out[:, 18] = seq[:, 19]
    out[:, 19] = seq[:, 22]
    out[:, 20] = seq[:, 20]
    return out


def draw_pose(mp, frame: np.ndarray, result) -> np.ndarray:
    out = frame.copy()
    if result.pose_landmarks is not None:
        mp.solutions.drawing_utils.draw_landmarks(
            out,
            result.pose_landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
        )
    return out


def predict_sequence(engine: PoseRuntimeEngine, sequence: np.ndarray) -> Dict:
    seq = np.asarray(sequence, dtype=np.float32)
    if seq.ndim != 3:
        raise ValueError(f"Expected [T, V, C], got {seq.shape}")
    if seq.shape[1] == 33 and seq.shape[2] >= 4:
        seq = adapt_mediapipe_33_to_shared21(seq)
    if seq.shape[1] != 21 or seq.shape[2] < 4:
        raise ValueError(f"Pose ONNX expects shape [T, 21, 4] or MediaPipe [T, 33, 4], got {seq.shape}")
    seq = seq[:, :, :4]
    probs = engine.session.run(["probs"], {"sequence": seq[None, ...]})[0][0]
    idx = int(np.argmax(probs))
    return {
        "modality": "pose",
        "label": engine.labels[idx],
        "score": float(probs[idx]),
        "extra": {
            "confidences": {engine.labels[i]: float(probs[i]) for i in range(len(engine.labels))},
            "num_frames": int(seq.shape[0]),
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def predict_frame(engine: PoseRuntimeEngine, frame: np.ndarray, state: Optional[PoseTurnState] = None):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = engine.pose.process(rgb)
    out = draw_pose(engine.mp, frame, result)
    pose_arr = pose_result_to_array(result)
    if pose_arr is None:
        return out, None

    turn_state = state or build_turn_state(engine.pose_window)
    turn_state.last_used_at = time.time()
    turn_state.pose_buffer.append(pose_arr)
    if len(turn_state.pose_buffer) < 8:
        return out, {
            "modality": "pose",
            "label": "collecting",
            "score": 0.0,
            "extra": {"frames": len(turn_state.pose_buffer)},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    pose_seq = np.stack(list(turn_state.pose_buffer), axis=0)
    pred = predict_sequence(engine, pose_seq)
    pred["extra"]["frames"] = len(turn_state.pose_buffer)
    pred["extra"]["adapter"] = "mediapipe33_to_shared21_joint_mapping"
    return out, pred


def close_runtime_engine(engine: PoseRuntimeEngine) -> None:
    engine.pose.close()
