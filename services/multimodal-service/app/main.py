from __future__ import annotations

"""FastAPI entrypoint for the multimodal-service runtime."""

# Keep this module lightweight so Docker rebuild tests only touch the app layer.

from fastapi import FastAPI

from app.api.multimodal import router as multimodal_router
from app.api.non_eeg_inference import legacy_router, router as non_eeg_inference_router
from app.config import get_settings
from app.services.multimodal_store import (
    recover_incomplete_audio_turns,
    shutdown_transcription_executor,
)
from app.services.non_eeg_runtime import runtime_store
from app.services.object_storage import ensure_multimodal_bucket
from app.services.responses import success_response

settings = get_settings()
app = FastAPI(title=settings["app_name"], version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    settings["runtime_assets_dir"].mkdir(parents=True, exist_ok=True)
    settings["upload_processing_dir"].mkdir(parents=True, exist_ok=True)
    settings["dolphin_model_dir"].mkdir(parents=True, exist_ok=True)
    recover_incomplete_audio_turns()
    try:
        ensure_multimodal_bucket()
    except Exception:
        pass


@app.on_event("shutdown")
def shutdown() -> None:
    shutdown_transcription_executor()
    runtime_store.shutdown()


@app.get("/health/live")
def health_live():
    return success_response({"status": "ok", "service": "multimodal-service"})


@app.get("/health/ready")
def health_ready():
    return success_response({"status": "ready", "service": "multimodal-service"})


app.include_router(non_eeg_inference_router)
app.include_router(legacy_router)
app.include_router(multimodal_router)
