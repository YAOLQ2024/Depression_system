from __future__ import annotations

import base64
from datetime import datetime
from mimetypes import guess_type
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.schemas import (
    CreateMultimodalSessionRequest,
    SubmitAudioTurnRequest,
    SubmitFrameCaptureRequest,
    WarmupMultimodalSessionRequest,
)
from app.services.multimodal_session_service import (
    MultimodalServiceError as SessionServiceError,
    get_multimodal_live,
    get_multimodal_session,
    get_multimodal_turn_bundle,
    submit_audio_turn,
    submit_face_capture,
    submit_pose_capture,
    warmup_multimodal_session,
)
from app.services.multimodal_store import (
    MultimodalServiceError as StoreServiceError,
    create_audio_turn,
    create_or_get_multimodal_session,
    get_audio_turn,
    preview_audio_chunk,
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
        raise HTTPException(
            status_code=400,
            detail=error_response(message="empty_image_file", code=4003),
        )
    return base64.b64encode(content).decode("ascii")


def _translate_error(
    exc: SessionServiceError | StoreServiceError,
) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


def _parse_optional_int(value: Any, *, field_name: str) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=error_response(message=f"invalid_{field_name}", code=4221),
        ) from exc


def _parse_optional_datetime(value: Any, *, field_name: str) -> datetime | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        return value
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=error_response(message=f"invalid_{field_name}", code=4222),
        ) from exc


@router.post("/sessions")
def post_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_or_get_multimodal_session(payload, x_mcs_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"multimodal_session": session_payload},
        message="multimodal session created",
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        session_payload = get_multimodal_session(session_id, acting_user_id=x_mcs_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response({"multimodal_session": session_payload})


@router.post("/sessions/{session_id}/warmup")
def post_warmup(
    session_id: str,
    payload: WarmupMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = warmup_multimodal_session(
            session_id,
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"multimodal_session": session_payload},
        message="multimodal runtime warmed",
    )


@router.post("/sessions/{session_id}/audio-turns")
async def post_audio_turn(
    session_id: str,
    request: Request,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        if "multipart/form-data" in content_type:
            form = await request.form()
            audio_file = form.get("audio_file")
            if not isinstance(audio_file, StarletteUploadFile):
                raise HTTPException(
                    status_code=400,
                    detail=error_response(message="audio_file is required", code=4006),
                )
            audio_turn = await create_audio_turn(
                multimodal_session_id=session_id,
                consultation_session_id=str(form.get("consultation_session_id") or ""),
                question_key=str(form.get("question_key") or ""),
                prompt_key=str(form.get("prompt_key") or "") or None,
                stage_id=str(form.get("stage_id") or ""),
                node_id=str(form.get("node_id") or ""),
                duration_ms=_parse_optional_int(form.get("duration_ms"), field_name="duration_ms"),
                response_started_at=_parse_optional_datetime(
                    form.get("response_started_at"),
                    field_name="response_started_at",
                ),
                response_completed_at=_parse_optional_datetime(
                    form.get("response_completed_at"),
                    field_name="response_completed_at",
                ),
                mime_type=str(form.get("mime_type") or ""),
                turn_id=str(form.get("turn_id") or "") or None,
                audio_file=audio_file,
            )
            return success_response(
                {"audio_turn": audio_turn},
                message="audio turn uploaded",
            )

        payload = SubmitAudioTurnRequest.model_validate(await request.json())
        result = submit_audio_turn(
            session_id,
            payload,
            acting_user_id=x_mcs_user_id,
        )
        return success_response(result, message="audio turn accepted")
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc


@router.get("/sessions/{session_id}/audio-turns/{audio_turn_id}")
def get_audio_turn_status(session_id: str, audio_turn_id: str):
    try:
        audio_turn = get_audio_turn(session_id, audio_turn_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"audio_turn": audio_turn},
        message="audio turn status loaded",
    )


@router.post("/sessions/{session_id}/audio-preview")
async def post_audio_preview(
    session_id: str,
    request: Request,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        get_multimodal_session(session_id, acting_user_id=x_mcs_user_id)
        form = await request.form()
        audio_file = form.get("audio_file")
        if not isinstance(audio_file, StarletteUploadFile):
            raise HTTPException(
                status_code=400,
                detail=error_response(message="audio_file is required", code=4006),
            )
        mime_type = str(form.get("mime_type") or "")
        result = await preview_audio_chunk(
            multimodal_session_id=session_id,
            mime_type=mime_type,
            audio_file=audio_file,
        )
        return success_response(
            {"audio_preview": result},
            message="audio preview transcribed",
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc


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
    except (SessionServiceError, StoreServiceError) as exc:
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
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="pose capture accepted")


@router.get("/sessions/{session_id}/live")
def get_live(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        result = get_multimodal_live(session_id, acting_user_id=x_mcs_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
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
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result)
