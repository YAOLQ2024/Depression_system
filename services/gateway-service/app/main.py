from urllib import error, request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessments import router as assessments_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.consultations import router as consultations_router
from app.api.multimodal import router as multimodal_router
from app.api.users import router as users_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings["app_name"], version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["cors_origins"],
    allow_origin_regex=settings["cors_origin_regex"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(consultations_router)
app.include_router(multimodal_router)
app.include_router(assessments_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "gateway-service"}


@app.get("/health/ready")
def health_ready():
    upstreams = [
        ("identity-service", settings["identity_service_url"]),
        ("consultation-service", settings["consultation_service_url"]),
        ("assessment-service", settings["assessment_service_url"]),
        ("multimodal-service", settings["multimodal_service_url"]),
    ]

    for service_name, base_url in upstreams:
        try:
            with request.urlopen(f"{base_url}/health/ready", timeout=5) as response:
                if response.status >= 400:
                    raise HTTPException(status_code=503, detail={"message": f"{service_name} not ready"})
        except HTTPException:
            raise
        except error.URLError as exc:
            raise HTTPException(status_code=503, detail={"message": f"{service_name} unavailable: {exc.reason}"}) from exc

    return {"status": "ready", "service": "gateway-service"}
