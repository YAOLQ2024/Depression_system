from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.consultations import router as consultations_router
from app.config import get_settings
from app.services.workflow_loader import get_workflow_loader

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_workflow_loader().load_bundle()
    yield


app = FastAPI(title=settings["app_name"], version="0.1.0", lifespan=lifespan)
app.include_router(consultations_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "consultation-service"}


@app.get("/health/ready")
def health_ready():
    bundle = get_workflow_loader().load_bundle()
    return {
        "status": "ready",
        "service": "consultation-service",
        "workflow_id": bundle.workflow_id,
        "script_bundle": bundle.script_bundle,
    }
