from __future__ import annotations

from fastapi import FastAPI

from app.api.multimodal import router as multimodal_router
from app.config import get_settings
from app.services.multimodal_store import (
    recover_incomplete_audio_turns,
    shutdown_transcription_executor,
)
from app.services.object_storage import ensure_multimodal_bucket

settings = get_settings()
app = FastAPI(title=settings["app_name"], version="0.1.0")

app.include_router(multimodal_router)


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


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "multimodal-service"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "multimodal-service"}
