from __future__ import annotations

from fastapi import FastAPI

from app.api.interventions import router as interventions_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings["app_name"], version="0.1.0")

app.include_router(interventions_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "intervention-service"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "intervention-service"}
