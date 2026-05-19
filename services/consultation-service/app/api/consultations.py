from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.schemas.consultations import (
    ConsultationSubtitlePreviewRequest,
    ConsultationTurnRequest,
    CreateConsultationSessionRequest,
)
from app.services.consultation_engine import (
    ConsultationServiceError,
    complete_system_question_item,
    create_consultation_session,
    get_consultation_multimodal_live,
    get_consultation_session,
    get_consultation_turn_detail,
    get_consultation_turn_multimodal_bundle,
    sync_consultation_subtitle_preview,
    start_consultation_session,
    submit_consultation_audio_turn,
    submit_consultation_face_capture,
    submit_consultation_pose_capture,
    submit_consultation_turn,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1", tags=["consultations"])


def _translate_error(exc: ConsultationServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.post("/consultations")
def post_consultation(
    payload: CreateConsultationSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_consultation_session(
            payload, acting_user_id=x_mcs_user_id
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"consultation": session_payload},
        message="consultation session created",
    )


@router.get("/consultations/{session_id}")
def get_consultation(
    session_id: str, x_mcs_user_id: str | None = Header(default=None)
):
    try:
        session_payload = get_consultation_session(
            session_id, acting_user_id=x_mcs_user_id
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload})


@router.post("/consultations/{session_id}/start")
def post_consultation_start(
    session_id: str, x_mcs_user_id: str | None = Header(default=None)
):
    try:
        session_payload = start_consultation_session(
            session_id, acting_user_id=x_mcs_user_id
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"consultation": session_payload}, message="consultation started"
    )


@router.post("/consultations/{session_id}/question-items/{question_key}/complete")
def post_system_question_item_complete(
    session_id: str,
    question_key: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = complete_system_question_item(
            session_id,
            question_key=question_key,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"consultation": session_payload},
        message="system question item completed",
    )


@router.post("/consultations/{session_id}/turns")
def post_consultation_turn(
    session_id: str,
    payload: ConsultationTurnRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = submit_consultation_turn(
            session_id, payload, acting_user_id=x_mcs_user_id
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"consultation": session_payload},
        message="consultation turn accepted",
    )


@router.post("/consultations/{session_id}/turns/audio")
async def post_consultation_audio_turn(
    session_id: str,
    transcript_text: str | None = Form(default=None),
    response_started_at: datetime | None = Form(default=None),
    response_completed_at: datetime | None = Form(default=None),
    mime_type: str | None = Form(default=None),
    audio_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        response_payload = submit_consultation_audio_turn(
            session_id,
            transcript_text=transcript_text,
            response_started_at=response_started_at,
            response_completed_at=response_completed_at,
            file_bytes=await audio_file.read(),
            filename=audio_file.filename,
            mime_type=mime_type or audio_file.content_type,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        response_payload,
        message="consultation speech turn accepted",
    )


@router.get("/consultations/{session_id}/turns/{turn_id}")
def get_consultation_turn_detail_route(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        turn_payload = get_consultation_turn_detail(
            session_id,
            turn_id,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(turn_payload)


@router.post("/consultations/{session_id}/subtitle-preview")
def post_consultation_subtitle_preview(
    session_id: str,
    payload: ConsultationSubtitlePreviewRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = sync_consultation_subtitle_preview(
            session_id,
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"consultation": session_payload},
        message="consultation subtitle preview synced",
    )


@router.get("/consultations/{session_id}/multimodal/live")
def get_consultation_live(
    session_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        live_payload = get_consultation_multimodal_live(
            session_id, acting_user_id=x_mcs_user_id
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(live_payload)


@router.get("/consultations/{session_id}/turns/{turn_id}/multimodal/bundle")
def get_consultation_turn_bundle(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        bundle_payload = get_consultation_turn_multimodal_bundle(
            session_id,
            turn_id,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(bundle_payload)


@router.post("/consultations/{session_id}/multimodal/captures/face")
async def post_consultation_face_capture(
    session_id: str,
    question_key: str = Form(...),
    turn_id: str | None = Form(default=None),
    capture_started_at: str = Form(...),
    capture_ended_at: str = Form(...),
    frame_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = submit_consultation_face_capture(
            session_id,
            question_key=question_key,
            consultation_turn_id=turn_id,
            capture_started_at=capture_started_at,
            capture_ended_at=capture_ended_at,
            frame_index=frame_index,
            mime_type=mime_type,
            filename=image_file.filename or f"face-{frame_index}.bin",
            file_bytes=await image_file.read(),
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(payload, message="consultation face capture accepted")


@router.post("/consultations/{session_id}/multimodal/captures/pose")
async def post_consultation_pose_capture(
    session_id: str,
    question_key: str = Form(...),
    turn_id: str | None = Form(default=None),
    capture_started_at: str = Form(...),
    capture_ended_at: str = Form(...),
    frame_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = submit_consultation_pose_capture(
            session_id,
            question_key=question_key,
            consultation_turn_id=turn_id,
            capture_started_at=capture_started_at,
            capture_ended_at=capture_ended_at,
            frame_index=frame_index,
            mime_type=mime_type,
            filename=image_file.filename or f"pose-{frame_index}.bin",
            file_bytes=await image_file.read(),
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(payload, message="consultation pose capture accepted")
