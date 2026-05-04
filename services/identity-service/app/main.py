from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.config import get_settings
from app.services.user_store import ensure_seed_users

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_seed_users()
    yield


app = FastAPI(title=settings["app_name"], version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "identity-service"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "identity-service"}
