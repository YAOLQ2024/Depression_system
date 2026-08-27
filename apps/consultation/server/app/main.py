from pathlib import Path
import re
from typing import Annotated, Iterator

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

CLIENT_DIST_DIR = Path(__file__).resolve().parents[2] / "client" / "dist"
CLIENT_ASSETS_DIR = CLIENT_DIST_DIR / "assets"
OCEAN_VIDEO_PATH = CLIENT_DIST_DIR / "intervention" / "video" / "ocean-h264.mp4"
VIDEO_CHUNK_SIZE = 1024 * 1024
BYTE_RANGE_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

app = FastAPI(title="Consultation App Server")


def resolve_byte_range(range_header: str | None, file_size: int) -> tuple[int, int, bool]:
    if not range_header:
        return 0, file_size - 1, False

    match = BYTE_RANGE_PATTERN.fullmatch(range_header.strip())
    if not match:
        raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    start_text, end_text = match.groups()
    if not start_text and not end_text:
        raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    if not start_text:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
        return max(file_size - suffix_length, 0), file_size - 1, True

    start = int(start_text)
    end = int(end_text) if end_text else file_size - 1
    if start >= file_size or start > end:
        raise HTTPException(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    return start, min(end, file_size - 1), True


def stream_file_segment(path: Path, start: int, content_length: int) -> Iterator[bytes]:
    with path.open("rb") as file:
        file.seek(start)
        remaining = content_length
        while remaining > 0:
            chunk = file.read(min(VIDEO_CHUNK_SIZE, remaining))
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk


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


@app.get("/intervention/video/ocean-h264.mp4")
def ocean_video(range_header: Annotated[str | None, Header(alias="Range")] = None):
    if not OCEAN_VIDEO_PATH.is_file():
        raise HTTPException(status_code=404, detail="Ocean video is unavailable")

    file_size = OCEAN_VIDEO_PATH.stat().st_size
    start, end, is_partial = resolve_byte_range(range_header, file_size)
    content_length = end - start + 1
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
    }
    if is_partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    return StreamingResponse(
        stream_file_segment(OCEAN_VIDEO_PATH, start, content_length),
        status_code=206 if is_partial else 200,
        media_type="video/mp4",
        headers=headers,
    )


@app.get("/config.js")
def config_script():
    return FileResponse(CLIENT_DIST_DIR / "config.js", headers=NO_STORE_HEADERS)


@app.get("/{full_path:path}")
def spa_routes(full_path: str):
    candidate = CLIENT_DIST_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(CLIENT_DIST_DIR / "index.html", headers=NO_STORE_HEADERS)
