from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

CLIENT_DIST_DIR = Path(__file__).resolve().parents[2] / "client" / "dist"
CLIENT_ASSETS_DIR = CLIENT_DIST_DIR / "assets"
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

app = FastAPI(title="Consultation App Server")


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "consultation-app-server"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "consultation-app-server"}


@app.get("/")
def index():
    return FileResponse(CLIENT_DIST_DIR / "index.html", headers=NO_STORE_HEADERS)


app.mount("/assets", StaticFiles(directory=CLIENT_ASSETS_DIR), name="consultation-assets")


@app.get("/config.js")
def config_script():
    return FileResponse(CLIENT_DIST_DIR / "config.js", headers=NO_STORE_HEADERS)


@app.get("/{full_path:path}")
def spa_routes(full_path: str):
    candidate = CLIENT_DIST_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(CLIENT_DIST_DIR / "index.html", headers=NO_STORE_HEADERS)
