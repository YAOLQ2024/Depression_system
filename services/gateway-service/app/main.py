from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessments import router as assessments_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.consultations import router as consultations_router
from app.api.users import router as users_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings["app_name"], version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(consultations_router)
app.include_router(assessments_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "gateway-service"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "gateway-service"}
