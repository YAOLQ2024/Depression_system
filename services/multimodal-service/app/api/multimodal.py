from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

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
def post_face_capture(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        result = submit_face_capture(session_id, payload, acting_user_id=x_mcs_user_id)
    except MultimodalServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="face capture accepted")


@router.post("/sessions/{session_id}/captures/pose")
def post_pose_capture(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
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
    return success_response({"turn_bundle": result})
