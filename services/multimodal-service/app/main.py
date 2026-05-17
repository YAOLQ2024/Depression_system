from __future__ import annotations

from fastapi import FastAPI

from app.api.multimodal import router as multimodal_router
from app.api.non_eeg_inference import legacy_router, router as non_eeg_inference_router
from app.config import get_settings
from app.services.non_eeg_runtime import runtime_store
from app.services.responses import success_response

settings = get_settings()
app = FastAPI(title=settings["app_name"], version="0.1.0")


@app.get("/health/live")
def health_live():
    return success_response({"status": "ok", "service": "multimodal-service"})


@app.get("/health/ready")
def health_ready():
    return success_response({"status": "ready", "service": "multimodal-service"})


@app.on_event("shutdown")
def on_shutdown() -> None:
    runtime_store.shutdown()


app.include_router(non_eeg_inference_router)
app.include_router(legacy_router)
app.include_router(multimodal_router)
