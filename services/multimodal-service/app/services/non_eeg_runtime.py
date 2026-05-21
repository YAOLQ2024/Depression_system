from __future__ import annotations

import logging
import sys
import threading
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
from infer_pose import close_runtime_engine as close_pose_runtime_engine  # type: ignore

logger = logging.getLogger(__name__)


class NonEegRuntimeStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}
        self._pose_engines: dict[str, Any] = {}

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

    def get_pose_engine(self, session_id: str | None = None):
        key = str(session_id).strip() if session_id else "default"
        engine = self._pose_engines.get(key)
        if engine is not None:
            return engine
        with self._lock:
            engine = self._pose_engines.get(key)
            if engine is None:
                engine = build_pose_runtime_engine(
                    model_path=str(POSE_DIR / "model.onnx"),
                    pose_window=settings["pose_window"],
                    providers=self._providers(),
                )
                self._pose_engines[key] = engine
        return engine

    def shutdown(self) -> None:
        with self._lock:
            for engine in self._pose_engines.values():
                try:
                    close_pose_runtime_engine(engine)
                except Exception:
                    pass
            self._pose_engines.clear()
            self._cache.clear()

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
