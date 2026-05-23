from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.schemas.consultations import (
    ConsultationTurnRequest,
    CreateConsultationSessionRequest,
)
from app.services.consultation_engine import (
    ConsultationServiceError,
    complete_system_question_item,
    create_consultation_session,
    get_consultation_multimodal_live,
    get_consultation_session,
    get_consultation_turn_multimodal_bundle,
    start_consultation_session,
    submit_consultation_face_capture,
    submit_consultation_pose_capture,
    submit_consultation_visual_capture,
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
    sample_started_at: str = Form(...),
    sample_ended_at: str = Form(...),
    sample_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = submit_consultation_face_capture(
            session_id,
            question_key=question_key,
            turn_id=turn_id,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            sample_index=sample_index,
            mime_type=mime_type,
            filename=image_file.filename or f"face-{sample_index}.bin",
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
    sample_started_at: str = Form(...),
    sample_ended_at: str = Form(...),
    sample_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = submit_consultation_pose_capture(
            session_id,
            question_key=question_key,
            turn_id=turn_id,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            sample_index=sample_index,
            mime_type=mime_type,
            filename=image_file.filename or f"pose-{sample_index}.bin",
            file_bytes=await image_file.read(),
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(payload, message="consultation pose capture accepted")


@router.post("/consultations/{session_id}/multimodal/captures/visual")
async def post_consultation_visual_capture(
    session_id: str,
    question_key: str = Form(...),
    turn_id: str | None = Form(default=None),
    sample_started_at: str = Form(...),
    sample_ended_at: str = Form(...),
    sample_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = submit_consultation_visual_capture(
            session_id,
            question_key=question_key,
            turn_id=turn_id,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            sample_index=sample_index,
            mime_type=mime_type,
            filename=image_file.filename or f"visual-{sample_index}.bin",
            file_bytes=await image_file.read(),
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(payload, message="consultation visual capture accepted")
