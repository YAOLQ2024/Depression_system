from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

CLIENT_DIR = Path(__file__).resolve().parents[2] / "client"

app = FastAPI(title="Consultation App Server")


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "consultation-app-server"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "consultation-app-server"}


@app.get("/")
def index():
    return FileResponse(CLIENT_DIR / "index.html")


app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="consultation-client")
