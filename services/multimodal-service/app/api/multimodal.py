from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.schemas.multimodal import CreateMultimodalSessionRequest
from app.services.multimodal_store import (
    MultimodalServiceError,
    create_audio_turn,
    create_or_get_multimodal_session,
    get_audio_turn,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1/multimodal", tags=["multimodal"])


def _proxy_error(exc: MultimodalServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(exc.message, exc.code),
    )


@router.post("/sessions")
def create_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_data = create_or_get_multimodal_session(payload, x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _proxy_error(exc) from exc
    return success_response(
        data={"multimodal_session": session_data},
        message="multimodal session ready",
    )


@router.post("/sessions/{session_id}/audio-turns")
async def upload_audio_turn(
    session_id: str,
    consultation_session_id: str = Form(...),
    question_key: str = Form(...),
    prompt_key: str | None = Form(default=None),
    stage_id: str = Form(...),
    node_id: str = Form(...),
    duration_ms: int | None = Form(default=None),
    response_started_at: datetime | None = Form(default=None),
    response_completed_at: datetime | None = Form(default=None),
    mime_type: str = Form(...),
    turn_id: str | None = Form(default=None),
    audio_file: UploadFile = File(...),
):
    try:
        audio_turn = await create_audio_turn(
            multimodal_session_id=session_id,
            consultation_session_id=consultation_session_id,
            question_key=question_key,
            prompt_key=prompt_key,
            stage_id=stage_id,
            node_id=node_id,
            duration_ms=duration_ms,
            response_started_at=response_started_at,
            response_completed_at=response_completed_at,
            mime_type=mime_type,
            turn_id=turn_id,
            audio_file=audio_file,
        )
    except MultimodalServiceError as exc:
        raise _proxy_error(exc) from exc
    return success_response(
        data={"audio_turn": audio_turn},
        message="audio turn uploaded",
    )


@router.get("/sessions/{session_id}/audio-turns/{audio_turn_id}")
def get_audio_turn_status(session_id: str, audio_turn_id: str):
    try:
        audio_turn = get_audio_turn(session_id, audio_turn_id)
    except MultimodalServiceError as exc:
        raise _proxy_error(exc) from exc
    return success_response(
        data={"audio_turn": audio_turn},
        message="audio turn status loaded",
    )
