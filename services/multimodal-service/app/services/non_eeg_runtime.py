from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

try:
    import tensorrt as trt
    import torch
except ImportError:
    trt = None
    torch = None
from app.config import get_settings

class _TensorMetadata:
    def __init__(self, name: str) -> None:
        self.name = name


def _torch_dtype(dtype):
    return torch.from_numpy(np.empty((), dtype=np.dtype(trt.nptype(dtype)))).dtype


class _TensorRTSession:
    def __init__(self, plan_path: Path) -> None:
        self._logger = trt.Logger(trt.Logger.ERROR)
        self._runtime = trt.Runtime(self._logger)
        self._engine = self._runtime.deserialize_cuda_engine(plan_path.read_bytes())
        if self._engine is None:
            raise RuntimeError(f"Cannot deserialize TensorRT engine: {plan_path}")
        self._context = self._engine.create_execution_context()
        self._input_names = [
            self._engine.get_tensor_name(index)
            for index in range(self._engine.num_io_tensors)
            if self._engine.get_tensor_mode(self._engine.get_tensor_name(index)) == trt.TensorIOMode.INPUT
        ]
        self._output_names = [
            self._engine.get_tensor_name(index)
            for index in range(self._engine.num_io_tensors)
            if self._engine.get_tensor_mode(self._engine.get_tensor_name(index)) == trt.TensorIOMode.OUTPUT
        ]

    def get_inputs(self):
        return [_TensorMetadata(name) for name in self._input_names]

    def get_outputs(self):
        return [_TensorMetadata(name) for name in self._output_names]

    def run(self, output_names, input_feed):
        tensors = {}
        for name in self._input_names:
            if name not in input_feed:
                raise ValueError(f"TensorRT input missing: {name}")
            expected_dtype = np.dtype(trt.nptype(self._engine.get_tensor_dtype(name)))
            value = np.ascontiguousarray(input_feed[name], dtype=expected_dtype)
            if not self._context.set_input_shape(name, tuple(value.shape)):
                raise ValueError(f"TensorRT shape is outside the optimization profile: {name}={value.shape}")
            tensors[name] = torch.as_tensor(value, device="cuda")
        for name in self._output_names:
            shape = tuple(self._context.get_tensor_shape(name))
            if any(dim < 0 for dim in shape):
                raise RuntimeError(f"TensorRT unresolved output shape: {name}={shape}")
            tensors[name] = torch.empty(shape, dtype=_torch_dtype(self._engine.get_tensor_dtype(name)), device="cuda")
        for name, tensor in tensors.items():
            if not self._context.set_tensor_address(name, tensor.data_ptr()):
                raise RuntimeError(f"TensorRT cannot bind tensor: {name}")
        stream = torch.cuda.current_stream()
        if not self._context.execute_async_v3(stream.cuda_stream):
            raise RuntimeError("TensorRT execution failed")
        stream.synchronize()
        selected = self._output_names if output_names is None else output_names
        return [tensors[name].detach().cpu().numpy() for name in selected]


_ORIGINAL_INFERENCE_SESSION = ort.InferenceSession
_TENSORRT_ENABLED = (
    os.getenv("MCS_TENSORRT_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    and trt is not None
    and torch is not None
    and torch.cuda.is_available()
)


def _inference_session(model_path, *args, **kwargs):
    plan_path = Path(model_path).with_suffix(".plan")
    if _TENSORRT_ENABLED and plan_path.is_file():
        logger.info("Using TensorRT GPU engine: %s", plan_path)
        return _TensorRTSession(plan_path)
    return _ORIGINAL_INFERENCE_SESSION(model_path, *args, **kwargs)


if _TENSORRT_ENABLED:
    ort.InferenceSession = _inference_session


settings = get_settings()
TEXT_DIR = Path(settings["text_model_dir"])
AUDIO_DIR = Path(settings["audio_model_dir"])
FACE_DIR = Path(settings["face_model_dir"])
POSE_DIR = Path(settings["pose_model_dir"])

for module_dir in (TEXT_DIR, AUDIO_DIR, FACE_DIR, POSE_DIR):
    sys.path.insert(0, str(module_dir))

from infer_text import build_runtime_engine as build_text_runtime_engine  # type: ignore
from infer_audio import build_runtime_engine as build_audio_runtime_engine  # type: ignore
from infer_face import build_runtime_engine as build_face_runtime_engine  # type: ignore
from infer_pose import build_runtime_engine as build_pose_runtime_engine  # type: ignore
from infer_pose import build_turn_state as build_pose_turn_state  # type: ignore
from infer_pose import close_runtime_engine as close_pose_runtime_engine  # type: ignore

logger = logging.getLogger(__name__)


class NonEegRuntimeStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}
        self._pose_turn_states: dict[str, Any] = {}

    def _providers(self) -> list[str]:
        requested = list(settings["model_providers"])
        available = set(ort.get_available_providers())
        selected = [provider for provider in requested if provider in available]
        if not selected:
            selected = ["CPUExecutionProvider"]
        logger.info(
            "Resolved ONNX providers requested=%s available=%s selected=%s",
            requested,
            sorted(available),
            selected,
        )
        return selected

    def get_text_engine(self):
        return self._get_cached(
            "text_emotion",
            lambda: build_text_runtime_engine(
                model_dir=str(TEXT_DIR),
                model_path=str(TEXT_DIR / "model.onnx"),
                providers=self._providers(),
            ),
        )

    def get_audio_engine(self):
        return self._get_cached(
            "audio_emotion",
            lambda: build_audio_runtime_engine(
                model_dir=str(AUDIO_DIR),
                model_path=str(AUDIO_DIR / "model.onnx"),
                providers=self._providers(),
            ),
        )

    def get_face_engine(self):
        return self._get_cached(
            "face_emotion",
            lambda: build_face_runtime_engine(
                model_path=str(FACE_DIR / "model.onnx"),
                providers=self._providers(),
            ),
        )

    def get_pose_engine(self):
        return self._get_cached(
            "pose_emotion",
            lambda: build_pose_runtime_engine(
                model_path=str(POSE_DIR / "model.onnx"),
                pose_window=settings["pose_window"],
                providers=self._providers(),
            ),
        )

    def get_pose_turn_state(
        self,
        session_id: str | None = None,
        turn_id: str | None = None,
    ):
        self.prune_pose_turn_states(settings["pose_state_idle_ttl_seconds"])
        key = self._build_pose_state_key(session_id, turn_id)
        state = self._pose_turn_states.get(key)
        if state is not None:
            state.last_used_at = time.time()
            return state
        with self._lock:
            state = self._pose_turn_states.get(key)
            if state is None:
                state = build_pose_turn_state(settings["pose_window"])
                self._pose_turn_states[key] = state
            state.last_used_at = time.time()
        return state

    def clear_pose_turn_state(
        self,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> bool:
        key = self._build_pose_state_key(session_id, turn_id)
        with self._lock:
            return self._pose_turn_states.pop(key, None) is not None

    def prune_pose_turn_states(self, idle_ttl_seconds: int) -> int:
        now = time.time()
        ttl = max(1, int(idle_ttl_seconds))
        with self._lock:
            expired_keys = [
                key
                for key, state in self._pose_turn_states.items()
                if (now - float(getattr(state, "last_used_at", 0.0))) > ttl
            ]
            for key in expired_keys:
                self._pose_turn_states.pop(key, None)
            return len(expired_keys)

    def shutdown(self) -> None:
        with self._lock:
            pose_engine = self._cache.get("pose_emotion")
            if pose_engine is not None:
                try:
                    close_pose_runtime_engine(pose_engine)
                except Exception:
                    pass
            self._pose_turn_states.clear()
            self._cache.clear()

    def _build_pose_state_key(
        self,
        session_id: str | None,
        turn_id: str | None,
    ) -> str:
        session_key = str(session_id).strip() if session_id else "default-session"
        turn_key = str(turn_id).strip() if turn_id else "default-turn"
        return f"{session_key}:{turn_key}"

    def _get_cached(self, key: str, builder):
        engine = self._cache.get(key)
        if engine is not None:
            return engine
        with self._lock:
            engine = self._cache.get(key)
            if engine is None:
                engine = builder()
                self._cache[key] = engine
        return engine


runtime_store = NonEegRuntimeStore()
