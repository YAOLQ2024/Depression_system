from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.config import get_settings
from app.database import get_db_session, get_engine
from app.services.user_store import ensure_seed_users

settings = get_settings()
REQUIRED_TABLES = {"users", "sessions"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_seed_users()
    yield


app = FastAPI(title=settings["app_name"], version="0.1.0", lifespan=lifespan)

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


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "identity-service"}


@app.get("/health/ready")
def health_ready():
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        existing_tables = set(inspect(get_engine()).get_table_names())
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"message": f"database not ready: {exc}"}) from exc

    missing_tables = sorted(REQUIRED_TABLES - existing_tables)
    if missing_tables:
        raise HTTPException(status_code=503, detail={"message": f"missing tables: {', '.join(missing_tables)}"})

    return {"status": "ready", "service": "identity-service"}
