from __future__ import annotations

"""FastAPI entrypoint for the multimodal-service runtime."""

# Keep this module lightweight so Docker rebuild tests only touch the app layer.

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.eeg_explanations import router as eeg_explanations_router
from app.api.multimodal import router as multimodal_router
from app.api.non_eeg_inference import legacy_router, router as non_eeg_inference_router
from app.config import get_settings
from app.redis import close_redis_client
from app.services.eeg_runtime import eeg_runtime_service
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
    settings["eeg_root"].mkdir(parents=True, exist_ok=True)
    settings["upload_processing_dir"].mkdir(parents=True, exist_ok=True)
    settings["dolphin_model_dir"].mkdir(parents=True, exist_ok=True)
    recover_incomplete_audio_turns()
    try:
        eeg_runtime_service.warmup_model()
        if settings["eeg_auto_start_transport"]:
            eeg_runtime_service.ensure_transport_started()
    except Exception:
        pass
    try:
        ensure_multimodal_bucket()
    except Exception:
        pass


@app.on_event("shutdown")
def shutdown() -> None:
    shutdown_transcription_executor()
    runtime_store.shutdown()
    eeg_runtime_service.shutdown()
    close_redis_client()


@app.get("/health/live")
def health_live():
    return success_response({"status": "ok", "service": "multimodal-service"})


@app.get("/health/ready")
def health_ready():
    eeg_status = eeg_runtime_service.status_snapshot()
    ready = bool(eeg_status.get("ready", True))
    return JSONResponse(
        status_code=200 if ready else 503,
        content=success_response(
            {
                "status": "ready" if ready else "not_ready",
                "service": "multimodal-service",
                "eeg": eeg_status,
            }
        ),
    )


app.include_router(non_eeg_inference_router)
app.include_router(legacy_router)
app.include_router(multimodal_router)
app.include_router(eeg_explanations_router)
