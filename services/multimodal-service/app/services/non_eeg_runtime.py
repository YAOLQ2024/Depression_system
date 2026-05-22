from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

import onnxruntime as ort
from app.config import get_settings

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
