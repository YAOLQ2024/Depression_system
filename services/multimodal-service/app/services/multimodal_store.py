from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import uuid

from fastapi import UploadFile
from minio.error import S3Error
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalAudioTurn, MultimodalSession
from app.schemas.multimodal import CreateMultimodalSessionRequest
from app.services.asr_runtime import DolphinAsrError, get_asr_runtime
from app.services.audio_processing import (
    AudioProcessingError,
    cleanup_processing_directory,
    convert_to_wav,
    ensure_processing_directory,
    get_wav_duration_ms,
    resolve_audio_suffix,
    resolve_mime_type,
    write_source_audio_file,
)
from app.services.object_storage import ensure_multimodal_bucket, upload_audio_object


class MultimodalServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


_TRANSCRIPTION_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="multimodal-dolphin-asr",
)
_ACTIVE_TRANSCRIPTION_FUTURES: dict[str, Future] = {}
_ACTIVE_TRANSCRIPTION_LOCK = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_stage_context(stage_context: dict | None) -> dict:
    return stage_context or {}


def _default_modalities(enabled_modalities: list[str] | None) -> list[str]:
    normalized = list(enabled_modalities or [])
    return normalized or ["text", "audio", "face", "pose"]


def _serialize_session(record: MultimodalSession) -> dict:
    started_at = record.started_at or record.created_at
    created_at = record.created_at or started_at
    return {
        "id": record.id,
        "session_id": record.id,
        "owner_service": record.owner_service,
        "owner_session_id": record.owner_session_id,
        "user_id": record.user_id,
        "stage_context": _serialize_stage_context(record.stage_context),
        "status": record.status,
        "enabled_modalities": _default_modalities(record.enabled_modalities),
        "latest_live_payload": dict(record.latest_live_payload or {}),
        "session_summary_payload": record.session_summary_payload,
        "notes": record.notes,
        "started_at": started_at.isoformat() if started_at else None,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": record.updated_at.isoformat(),
        "warmed_up_at": (
            record.warmed_up_at.isoformat() if record.warmed_up_at else None
        ),
        "completed_at": (
            record.completed_at.isoformat() if record.completed_at else None
        ),
    }


def _serialize_audio_turn(record: MultimodalAudioTurn) -> dict:
    return {
        "audio_turn_id": record.id,
        "session_id": record.multimodal_session_id,
        "consultation_session_id": record.consultation_session_id,
        "question_key": record.question_key,
        "processing_status": record.processing_status,
        "audio_uri": record.audio_uri,
        "transcript_text": record.transcript_text,
        "transcript_confidence": record.transcript_confidence,
        "asr_provider": record.asr_provider,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "response_started_at": (
            record.response_started_at.isoformat()
            if record.response_started_at
            else None
        ),
        "response_completed_at": (
            record.response_completed_at.isoformat()
            if record.response_completed_at
            else None
        ),
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _serialize_audio_preview(
    multimodal_session_id: str,
    transcript_text: str,
    transcript_confidence: float | None,
    resolved_device: str,
    duration_ms: int,
) -> dict:
    return {
        "session_id": multimodal_session_id,
        "transcript_text": transcript_text,
        "transcript_confidence": transcript_confidence,
        "resolved_device": resolved_device,
        "duration_ms": duration_ms,
        "asr_provider": "dolphin",
    }


def _translate_processing_error(exc: Exception) -> MultimodalServiceError:
    if isinstance(exc, AudioProcessingError):
        return MultimodalServiceError(
            exc.message,
            code=4151 if exc.error_code == "UNSUPPORTED_MIME_TYPE" else 4004,
            status_code=exc.status_code,
        )
    if isinstance(exc, DolphinAsrError):
        return MultimodalServiceError(
            exc.message,
            code=5032 if exc.error_code == "MODEL_NOT_READY" else 5002,
            status_code=503 if exc.error_code == "MODEL_NOT_READY" else 500,
        )
    if isinstance(exc, S3Error):
        return MultimodalServiceError(
            "object storage is unavailable",
            code=5031,
            status_code=503,
        )
    return MultimodalServiceError("audio processing failed", code=5001, status_code=500)


def _validate_audio_turn_fields(
    consultation_session_id: str,
    question_key: str,
    stage_id: str,
    node_id: str,
    mime_type: str,
    duration_ms: int | None,
    response_started_at: datetime | None,
    response_completed_at: datetime | None,
) -> None:
    if not consultation_session_id:
        raise MultimodalServiceError(
            "consultation_session_id is required",
            code=4001,
        )
    if not question_key:
        raise MultimodalServiceError("question_key is required", code=4002)
    if not stage_id:
        raise MultimodalServiceError("stage_id is required", code=4003)
    if not node_id:
        raise MultimodalServiceError("node_id is required", code=4004)
    if not mime_type:
        raise MultimodalServiceError("mime_type is required", code=4005)
    if duration_ms is not None and duration_ms <= 0:
        raise MultimodalServiceError(
            "duration_ms must be greater than zero",
            code=4009,
        )
    if (
        response_started_at is not None
        and response_completed_at is not None
        and response_completed_at < response_started_at
    ):
        raise MultimodalServiceError(
            "response_completed_at must be greater than response_started_at",
            code=4010,
        )


def _build_audio_object_key(
    consultation_session_id: str,
    question_key: str,
    audio_turn_id: str,
    suffix: str,
) -> str:
    return (
        f"consultation/{consultation_session_id}/{question_key}/"
        f"{audio_turn_id}{suffix}"
    )


def _update_audio_turn_for_restart_failure(audio_turn_id: str) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        if record.processing_status not in {"uploaded", "transcribing"}:
            return
        record.processing_status = "failed"
        record.error_code = "SERVICE_RESTARTED"
        record.error_message = "asr processing was interrupted by service restart"
        record.updated_at = _now()


def _mark_audio_turn_transcribing(audio_turn_id: str) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None or record.processing_status != "uploaded":
            return
        record.processing_status = "transcribing"
        record.updated_at = _now()


def _complete_audio_turn(
    audio_turn_id: str,
    transcript_text: str,
    transcript_confidence: float | None,
) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        record.processing_status = "completed"
        record.transcript_text = transcript_text
        record.transcript_confidence = transcript_confidence
        record.error_code = None
        record.error_message = None
        record.updated_at = _now()


def _fail_audio_turn(
    audio_turn_id: str,
    error_code: str,
    error_message: str,
) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        record.processing_status = "failed"
        record.error_code = error_code
        record.error_message = error_message
        record.updated_at = _now()


def _remove_active_future(audio_turn_id: str) -> None:
    with _ACTIVE_TRANSCRIPTION_LOCK:
        _ACTIVE_TRANSCRIPTION_FUTURES.pop(audio_turn_id, None)


def _run_transcription_job(audio_turn_id: str, wav_path: Path) -> None:
    try:
        _mark_audio_turn_transcribing(audio_turn_id)
        result = get_asr_runtime().transcribe(wav_path)
        _complete_audio_turn(
            audio_turn_id=audio_turn_id,
            transcript_text=result.transcript_text,
            transcript_confidence=result.transcript_confidence,
        )
    except DolphinAsrError as exc:
        _fail_audio_turn(audio_turn_id, exc.error_code, exc.message)
    except Exception as exc:
        _fail_audio_turn(audio_turn_id, "TRANSCRIPTION_FAILED", str(exc))
    finally:
        cleanup_processing_directory(audio_turn_id)
        _remove_active_future(audio_turn_id)


def _submit_transcription_job(audio_turn_id: str, wav_path: Path) -> Future:
    future = _TRANSCRIPTION_EXECUTOR.submit(
        _run_transcription_job,
        audio_turn_id,
        wav_path,
    )
    with _ACTIVE_TRANSCRIPTION_LOCK:
        _ACTIVE_TRANSCRIPTION_FUTURES[audio_turn_id] = future
    return future


def create_or_get_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    acting_user_id: str | None,
) -> dict:
    effective_user_id = acting_user_id or payload.user_id
    owner_service = payload.owner_service or "consultation-service"
    stage_context = (
        payload.stage_context.model_dump() if payload.stage_context else {}
    )
    enabled_modalities = _default_modalities(payload.enabled_modalities)

    with get_db_session() as db_session:
        existing = db_session.execute(
            select(MultimodalSession).where(
                MultimodalSession.owner_service == owner_service,
                MultimodalSession.owner_session_id == payload.owner_session_id,
            )
        ).scalar_one_or_none()
        if existing:
            now = _now()
            existing.user_id = effective_user_id or existing.user_id
            existing.stage_context = stage_context or existing.stage_context or {}
            existing.enabled_modalities = enabled_modalities
            existing.latest_live_payload = existing.latest_live_payload or {}
            existing.notes = payload.notes if payload.notes is not None else existing.notes
            existing.status = "ready"
            existing.started_at = existing.started_at or existing.created_at or now
            existing.created_at = existing.created_at or existing.started_at or now
            existing.updated_at = now
            db_session.flush()
            db_session.refresh(existing)
            return _serialize_session(existing)

        now = _now()
        record = MultimodalSession(
            id=str(uuid.uuid4()),
            owner_service=owner_service,
            owner_session_id=payload.owner_session_id,
            user_id=effective_user_id,
            stage_context=stage_context,
            status="ready",
            enabled_modalities=enabled_modalities,
            latest_live_payload={},
            notes=payload.notes,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add(record)
        db_session.flush()
        db_session.refresh(record)
        return _serialize_session(record)


def get_audio_turn(multimodal_session_id: str, audio_turn_id: str) -> dict:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if not record or record.multimodal_session_id != multimodal_session_id:
            raise MultimodalServiceError(
                "audio turn not found",
                code=4042,
                status_code=404,
            )
        return _serialize_audio_turn(record)


async def preview_audio_chunk(
    multimodal_session_id: str,
    mime_type: str,
    audio_file: UploadFile,
) -> dict:
    if not mime_type:
        raise MultimodalServiceError("mime_type is required", code=4005)

    try:
        get_asr_runtime().validate_model_assets()
    except Exception as exc:
        raise _translate_processing_error(exc) from exc

    with get_db_session() as db_session:
        session_record = db_session.get(MultimodalSession, multimodal_session_id)
        if not session_record:
            raise MultimodalServiceError(
                "multimodal session not found",
                code=4041,
                status_code=404,
            )

    file_bytes = await audio_file.read()
    if not file_bytes:
        raise MultimodalServiceError("audio_file is empty", code=4006)

    settings = get_settings()
    if len(file_bytes) > settings["upload_max_bytes"]:
        raise MultimodalServiceError(
            "audio file exceeds size limit",
            code=4007,
            status_code=413,
        )

    try:
        normalized_mime_type = resolve_mime_type(mime_type, audio_file.content_type)
        suffix = resolve_audio_suffix(normalized_mime_type, audio_file.filename)
    except Exception as exc:
        raise _translate_processing_error(exc) from exc

    preview_id = f"preview-{uuid.uuid4()}"
    processing_dir = ensure_processing_directory(preview_id)
    wav_path = processing_dir / "transcription.wav"

    try:
        source_path = write_source_audio_file(processing_dir, suffix, file_bytes)
        convert_to_wav(source_path, wav_path)
        actual_duration_ms = get_wav_duration_ms(wav_path)
        if actual_duration_ms <= 0:
            raise MultimodalServiceError("audio preview is empty", code=4006)
        if actual_duration_ms > settings["asr_preview_max_duration_ms"]:
            raise MultimodalServiceError(
                "audio preview duration exceeds limit",
                code=4011,
                status_code=413,
            )

        result = get_asr_runtime().transcribe(wav_path)
        return _serialize_audio_preview(
            multimodal_session_id=multimodal_session_id,
            transcript_text=result.transcript_text,
            transcript_confidence=result.transcript_confidence,
            resolved_device=result.resolved_device,
            duration_ms=actual_duration_ms,
        )
    except MultimodalServiceError:
        raise
    except Exception as exc:
        raise _translate_processing_error(exc) from exc
    finally:
        cleanup_processing_directory(preview_id)


async def create_audio_turn(
    multimodal_session_id: str,
    consultation_session_id: str,
    question_key: str,
    prompt_key: str | None,
    stage_id: str,
    node_id: str,
    duration_ms: int | None,
    response_started_at: datetime | None,
    response_completed_at: datetime | None,
    mime_type: str,
    turn_id: str | None,
    audio_file: UploadFile,
) -> dict:
    _validate_audio_turn_fields(
        consultation_session_id=consultation_session_id,
        question_key=question_key,
        stage_id=stage_id,
        node_id=node_id,
        mime_type=mime_type,
        duration_ms=duration_ms,
        response_started_at=response_started_at,
        response_completed_at=response_completed_at,
    )

    try:
        get_asr_runtime().validate_model_assets()
        ensure_multimodal_bucket()
    except Exception as exc:
        raise _translate_processing_error(exc) from exc

    with get_db_session() as db_session:
        session_record = db_session.get(MultimodalSession, multimodal_session_id)
        if not session_record:
            raise MultimodalServiceError(
                "multimodal session not found",
                code=4041,
                status_code=404,
            )
        if (
            session_record.owner_service == "consultation-service"
            and session_record.owner_session_id != consultation_session_id
        ):
            raise MultimodalServiceError(
                "consultation session mismatch",
                code=4091,
                status_code=409,
            )

    file_bytes = await audio_file.read()
    if not file_bytes:
        raise MultimodalServiceError("audio_file is empty", code=4006)

    settings = get_settings()
    if len(file_bytes) > settings["upload_max_bytes"]:
        raise MultimodalServiceError(
            "audio file exceeds size limit",
            code=4007,
            status_code=413,
        )

    try:
        normalized_mime_type = resolve_mime_type(mime_type, audio_file.content_type)
        suffix = resolve_audio_suffix(normalized_mime_type, audio_file.filename)
    except Exception as exc:
        raise _translate_processing_error(exc) from exc

    audio_turn_id = str(uuid.uuid4())
    processing_dir = ensure_processing_directory(audio_turn_id)
    source_path = processing_dir / f"source{suffix}"
    wav_path = processing_dir / "transcription.wav"

    try:
        source_path = write_source_audio_file(processing_dir, suffix, file_bytes)
        convert_to_wav(source_path, wav_path)
        actual_duration_ms = get_wav_duration_ms(wav_path)
        if actual_duration_ms > settings["upload_max_duration_ms"]:
            raise MultimodalServiceError(
                "audio duration exceeds limit",
                code=4008,
                status_code=413,
            )

        object_key = _build_audio_object_key(
            consultation_session_id=consultation_session_id,
            question_key=question_key,
            audio_turn_id=audio_turn_id,
            suffix=suffix,
        )
        audio_uri = upload_audio_object(
            object_key=object_key,
            file_bytes=file_bytes,
            content_type=normalized_mime_type,
        )

        now = _now()
        with get_db_session() as db_session:
            record = MultimodalAudioTurn(
                id=audio_turn_id,
                multimodal_session_id=multimodal_session_id,
                consultation_session_id=consultation_session_id,
                turn_id=turn_id,
                stage_id=stage_id,
                node_id=node_id,
                question_key=question_key,
                prompt_key=prompt_key,
                audio_uri=audio_uri,
                storage_provider="minio",
                storage_object_key=object_key,
                source_filename=audio_file.filename,
                mime_type=normalized_mime_type,
                file_size_bytes=len(file_bytes),
                duration_ms=actual_duration_ms,
                processing_status="uploaded",
                transcript_text=None,
                transcript_confidence=None,
                asr_provider="dolphin",
                error_code=None,
                error_message=None,
                response_started_at=response_started_at,
                response_completed_at=response_completed_at,
                created_at=now,
                updated_at=now,
            )
            db_session.add(record)

        future = _submit_transcription_job(audio_turn_id, wav_path)
        resolved_device = get_asr_runtime().resolve_device()
        if resolved_device == "cuda":
            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(future),
                    timeout=settings["asr_sync_timeout_ms"] / 1000,
                )
                return get_audio_turn(multimodal_session_id, audio_turn_id)
            except asyncio.TimeoutError:
                _mark_audio_turn_transcribing(audio_turn_id)
                return get_audio_turn(multimodal_session_id, audio_turn_id)

        _mark_audio_turn_transcribing(audio_turn_id)
        return get_audio_turn(multimodal_session_id, audio_turn_id)
    except MultimodalServiceError:
        cleanup_processing_directory(audio_turn_id)
        raise
    except Exception as exc:
        cleanup_processing_directory(audio_turn_id)
        raise _translate_processing_error(exc) from exc


def recover_incomplete_audio_turns() -> None:
    with get_db_session() as db_session:
        stale_ids = [
            record.id
            for record in db_session.execute(
                select(MultimodalAudioTurn).where(
                    MultimodalAudioTurn.processing_status.in_(
                        ["uploaded", "transcribing"]
                    )
                )
            ).scalars()
        ]

    for stale_id in stale_ids:
        _update_audio_turn_for_restart_failure(stale_id)


def shutdown_transcription_executor() -> None:
    _TRANSCRIPTION_EXECUTOR.shutdown(wait=False, cancel_futures=False)
