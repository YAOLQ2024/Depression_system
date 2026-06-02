from __future__ import annotations

from fastapi import FastAPI

from app.api.risk import router as risk_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings["app_name"], version="0.1.0")

app.include_router(risk_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "risk-service"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "risk-service"}
