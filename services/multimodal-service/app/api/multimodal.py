from __future__ import annotations

import base64
from mimetypes import guess_type

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.schemas import (
    CreateMultimodalSessionRequest,
    SubmitAudioTurnRequest,
    SubmitFrameCaptureRequest,
    WarmupMultimodalSessionRequest,
)
from app.services.multimodal_session_service import (
    MultimodalServiceError,
    create_multimodal_session,
    get_multimodal_live,
    get_multimodal_session,
    get_multimodal_turn_bundle,
    submit_audio_turn,
    submit_face_capture,
    submit_pose_capture,
    warmup_multimodal_session,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1/multimodal", tags=["multimodal"])


def _detect_image_format(mime_type: str, filename: str | None) -> str:
    normalized = str(mime_type or "").strip().lower()
    if "/" in normalized:
        _, _, subtype = normalized.partition("/")
        if subtype:
            return subtype
    guessed, _ = guess_type(filename or "")
    if guessed and "/" in guessed:
        return guessed.split("/", 1)[1]
    return "jpeg"


async def _to_base64(upload: UploadFile) -> str:
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail=error_response(message="empty_image_file", code=4003))
    return base64.b64encode(content).decode("ascii")


def _translate_error(exc: MultimodalServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.post("/sessions")
def post_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_multimodal_session(payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"multimodal_session": session_payload}, message="multimodal session created")


@router.get("/sessions/{session_id}")
def get_session(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        session_payload = get_multimodal_session(session_id, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"multimodal_session": session_payload})


@router.post("/sessions/{session_id}/warmup")
def post_warmup(
    session_id: str,
    payload: WarmupMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = warmup_multimodal_session(session_id, payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"multimodal_session": session_payload}, message="multimodal runtime warmed")


@router.post("/sessions/{session_id}/audio-turns")
def post_audio_turn(
    session_id: str,
    payload: SubmitAudioTurnRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        result = submit_audio_turn(session_id, payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="audio turn accepted")


@router.post("/sessions/{session_id}/captures/face")
async def post_face_capture(
    session_id: str,
    consultation_session_id: str = Form(...),
    question_key: str = Form(...),
    turn_id: str | None = Form(default=None),
    capture_started_at: str = Form(...),
    capture_ended_at: str = Form(...),
    frame_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    payload = SubmitFrameCaptureRequest(
        consultation_session_id=consultation_session_id,
        question_key=question_key,
        consultation_turn_id=turn_id,
        capture_started_at=capture_started_at,
        capture_ended_at=capture_ended_at,
        frame_index=frame_index,
        mime_type=mime_type,
        image_format=_detect_image_format(mime_type, image_file.filename),
        image_base64=await _to_base64(image_file),
        frame_id=f"face-{frame_index}",
    )
    try:
        result = submit_face_capture(session_id, payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="face capture accepted")


@router.post("/sessions/{session_id}/captures/pose")
async def post_pose_capture(
    session_id: str,
    consultation_session_id: str = Form(...),
    question_key: str = Form(...),
    turn_id: str | None = Form(default=None),
    capture_started_at: str = Form(...),
    capture_ended_at: str = Form(...),
    frame_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    payload = SubmitFrameCaptureRequest(
        consultation_session_id=consultation_session_id,
        question_key=question_key,
        consultation_turn_id=turn_id,
        capture_started_at=capture_started_at,
        capture_ended_at=capture_ended_at,
        frame_index=frame_index,
        mime_type=mime_type,
        image_format=_detect_image_format(mime_type, image_file.filename),
        image_base64=await _to_base64(image_file),
        frame_id=f"pose-{frame_index}",
    )
    try:
        result = submit_pose_capture(session_id, payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="pose capture accepted")


@router.get("/sessions/{session_id}/live")
def get_live(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        result = get_multimodal_live(session_id, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result)


@router.get("/sessions/{session_id}/turns/{consultation_turn_id}/bundle")
def get_turn_bundle(
    session_id: str,
    consultation_turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        result = get_multimodal_turn_bundle(
            session_id,
            consultation_turn_id,
            acting_user_id=x_mcs_user_id,
        )
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result)
