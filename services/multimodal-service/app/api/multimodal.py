from __future__ import annotations

from datetime import datetime
from mimetypes import guess_type
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.schemas import (
    CreateMultimodalSessionRequest,
    FinishEegTurnRequest,
    StartEegTurnRequest,
    SubmitAudioTurnRequest,
    SubmitFrameCaptureRequest,
    WarmupMultimodalSessionRequest,
)
from app.services.multimodal_live_stream import iter_multimodal_live_events
from app.services.multimodal_session_service import (
    clear_pose_turn_runtime_state,
    finalize_multimodal_turn,
    finish_eeg_turn,
    get_eeg_turn_results,
    MultimodalServiceError as SessionServiceError,
    get_multimodal_live,
    get_multimodal_session,
    get_multimodal_turn_bundle,
    recover_multimodal_turn_hot_state,
    start_eeg_turn,
    submit_audio_turn,
    submit_visual_capture,
    warmup_multimodal_session,
)
from app.services.multimodal_store import (
    MultimodalServiceError as StoreServiceError,
    create_audio_turn,
    create_or_get_multimodal_session,
    get_audio_turn,
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


async def _read_upload_bytes(upload: UploadFile) -> bytes:
    content = await upload.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail=error_response(message="empty_image_file", code=4003),
        )
    return content


def _translate_error(
    exc: SessionServiceError | StoreServiceError,
) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


def _require_acting_user_id(x_mcs_user_id: str | None) -> str:
    acting_user_id = str(x_mcs_user_id or "").strip()
    if acting_user_id:
        return acting_user_id
    raise HTTPException(
        status_code=401,
        detail=error_response(message="missing acting user id", code=4013),
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
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        session_payload = create_or_get_multimodal_session(payload, acting_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"multimodal_session": session_payload},
        message="multimodal session created",
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        session_payload = get_multimodal_session(session_id, acting_user_id=acting_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response({"multimodal_session": session_payload})


@router.post("/sessions/{session_id}/warmup")
def post_warmup(
    session_id: str,
    payload: WarmupMultimodalSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        session_payload = warmup_multimodal_session(
            session_id,
            payload,
            acting_user_id=acting_user_id,
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
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
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
                flow_run_id=str(form.get("flow_run_id") or ""),
                origin_flow_type=str(form.get("origin_flow_type") or "") or None,
                question_key=str(form.get("question_key") or ""),
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
                acting_user_id=acting_user_id,
            )
            return success_response(
                {"audio_turn": audio_turn},
                message="audio turn uploaded",
            )

        payload = SubmitAudioTurnRequest.model_validate(await request.json())
        result = submit_audio_turn(
            session_id,
            payload,
            acting_user_id=acting_user_id,
        )
        return success_response(result, message="audio turn accepted")
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc


@router.get("/sessions/{session_id}/audio-turns/{audio_turn_id}")
def get_audio_turn_status(
    session_id: str,
    audio_turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        audio_turn = get_audio_turn(
            session_id,
            audio_turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"audio_turn": audio_turn},
        message="audio turn status loaded",
    )


@router.post("/sessions/{session_id}/visual-captures")
async def post_visual_capture(
    session_id: str,
    flow_run_id: str = Form(...),
    origin_flow_type: str | None = Form(default=None),
    question_key: str = Form(...),
    stage_id: str | None = Form(default=None),
    turn_id: str | None = Form(default=None),
    sample_started_at: str = Form(...),
    sample_ended_at: str = Form(...),
    sample_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    image_bytes = await _read_upload_bytes(image_file)
    payload = SubmitFrameCaptureRequest(
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        question_key=question_key,
        stage_id=stage_id,
        turn_id=turn_id,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
        sample_index=sample_index,
        mime_type=mime_type,
        image_format=_detect_image_format(mime_type, image_file.filename),
        image_bytes=image_bytes,
        frame_id=f"visual-{sample_index}",
    )
    try:
        result = submit_visual_capture(session_id, payload, acting_user_id=acting_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="visual capture accepted")


@router.get("/sessions/{session_id}/live")
def get_live(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = get_multimodal_live(session_id, acting_user_id=acting_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result)


@router.get("/sessions/{session_id}/live/stream")
async def get_live_stream(
    session_id: str,
    request: Request,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        initial_snapshot = get_multimodal_live(
            session_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc

    async def event_stream():
        async for event in iter_multimodal_live_events(
            session_id=session_id,
            initial_snapshot=initial_snapshot,
            snapshot_loader=lambda: get_multimodal_live(
                session_id,
                acting_user_id=acting_user_id,
            ),
            disconnect_checker=request.is_disconnected,
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/{session_id}/eeg/turns/start")
def post_start_eeg_turn(
    session_id: str,
    payload: StartEegTurnRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = start_eeg_turn(session_id, payload, acting_user_id=acting_user_id)
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="eeg turn started")


@router.post("/sessions/{session_id}/eeg/turns/{turn_id}/finish")
def post_finish_eeg_turn(
    session_id: str,
    turn_id: str,
    payload: FinishEegTurnRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = finish_eeg_turn(
            session_id,
            turn_id,
            payload,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="eeg turn finished")


@router.get("/sessions/{session_id}/eeg/turns/{turn_id}/results")
def get_eeg_turn_result_list(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = get_eeg_turn_results(
            session_id,
            turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result)


@router.get("/sessions/{session_id}/turns/{turn_id}/bundle")
def get_turn_bundle(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = get_multimodal_turn_bundle(
            session_id,
            turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result)


@router.post("/sessions/{session_id}/turns/{turn_id}/finalize")
def post_finalize_turn(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = finalize_multimodal_turn(
            session_id,
            turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="turn finalized")


@router.post("/sessions/{session_id}/turns/{turn_id}/recover")
def post_recover_turn_hot_state(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = recover_multimodal_turn_hot_state(
            session_id,
            turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="turn hot state recovered")


@router.post("/sessions/{session_id}/turns/{turn_id}/pose-runtime/clear")
def post_clear_pose_turn_runtime(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    acting_user_id = _require_acting_user_id(x_mcs_user_id)
    try:
        result = clear_pose_turn_runtime_state(
            session_id,
            turn_id,
            acting_user_id=acting_user_id,
        )
    except (SessionServiceError, StoreServiceError) as exc:
        raise _translate_error(exc) from exc
    return success_response(result, message="pose turn runtime cleared")
