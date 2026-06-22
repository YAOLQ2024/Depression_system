from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import logging
from pathlib import Path
import threading
import uuid

from fastapi import UploadFile
from minio.error import S3Error
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalAudioTurn, MultimodalSession
from app.schemas.multimodal import CreateMultimodalSessionRequest, SubmitAudioTurnRequest
from app.services.asr_runtime import DolphinAsrError, get_asr_runtime
from app.services.multimodal_session_service import (
    MultimodalServiceError as SessionPipelineError,
    submit_audio_turn as process_audio_turn,
)
from app.services.audio_processing import (
    AudioProcessingError,
    cleanup_processing_directory,
    convert_to_wav,
    ensure_processing_directory,
    get_wav_duration_ms,
    resolve_audio_suffix,
    resolve_mime_type,
    trim_leading_silence,
    write_source_audio_file,
)
from app.services.multimodal_session_registry import (
    create_or_reuse_session_record,
)
from app.services.multimodal_session_scope import (
    session_allows_flow_run,
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
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_store_session_access(
    session_record: MultimodalSession,
    acting_user_id: str | None,
) -> None:
    if not acting_user_id:
        raise MultimodalServiceError(
            "missing acting user id",
            code=4013,
            status_code=401,
        )
    session_user_id = str(getattr(session_record, "user_id", None) or "").strip()
    if session_user_id and session_user_id != str(acting_user_id).strip():
        raise MultimodalServiceError(
            "multimodal session access denied",
            code=4031,
            status_code=403,
        )


def _serialize_stage_context(stage_context: dict | None) -> dict:
    return stage_context or {}


def _default_modalities(enabled_modalities: list[str] | None) -> list[str]:
    normalized = list(enabled_modalities or [])
    return normalized or ["text", "audio", "face", "pose", "eeg"]


def _serialize_session(record: MultimodalSession) -> dict:
    started_at = record.started_at or record.created_at
    created_at = record.created_at or started_at
    return {
        "id": record.id,
        "session_id": record.id,
        "encounter_session_id": record.encounter_session_id,
        "scope_type": record.scope_type,
        "scope_id": record.scope_id,
        "flow_type": record.flow_type,
        "flow_run_id": record.flow_run_id,
        "user_id": record.user_id,
        "stage_context": _serialize_stage_context(record.stage_context),
        "status": record.status,
        "enabled_modalities": _default_modalities(record.enabled_modalities),
        "live_state_payload": dict(record.live_state_payload or {}),
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
        "flow_run_id": record.flow_run_id,
        "origin_flow_type": record.origin_flow_type,
        "question_key": record.question_key,
        "processing_status": record.processing_status,
        "audio_uri": record.audio_uri,
        "normalized_wav_uri": record.normalized_wav_uri,
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


def _translate_processing_error(exc: Exception) -> MultimodalServiceError:
    if isinstance(exc, SessionPipelineError):
        return MultimodalServiceError(
            exc.message,
            code=exc.code,
            status_code=exc.status_code,
        )
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
    detail = str(exc).strip()
    return MultimodalServiceError(
        f"audio processing failed: {detail}" if detail else "audio processing failed",
        code=5001,
        status_code=500,
    )


def _validate_audio_turn_fields(
    flow_run_id: str,
    question_key: str,
    stage_id: str,
    node_id: str,
    mime_type: str,
    duration_ms: int | None,
    response_started_at: datetime | None,
    response_completed_at: datetime | None,
) -> None:
    if not flow_run_id:
        raise MultimodalServiceError(
            "flow_run_id is required",
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
    flow_run_id: str,
    question_key: str,
    audio_turn_id: str,
    suffix: str,
) -> str:
    return (
        f"consultation/{flow_run_id}/{question_key}/"
        f"{audio_turn_id}{suffix}"
    )


def _build_normalized_wav_object_key(
    flow_run_id: str,
    question_key: str,
    effective_turn_id: str,
) -> str:
    return (
        f"consultation/{flow_run_id}/{question_key}/"
        f"{effective_turn_id}.normalized.wav"
    )


def _update_audio_turn_for_restart_failure(audio_turn_id: str) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        if record.processing_status not in {
            "uploaded",
            "transcribing",
            "transcript_ready",
            "analyzing",
        }:
            return
        record.processing_status = "failed"
        record.error_code = "SERVICE_RESTARTED"
        record.error_message = "audio processing was interrupted by service restart"
        record.updated_at = _now()


def _mark_audio_turn_transcribing(audio_turn_id: str) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None or record.processing_status != "uploaded":
            return
        record.processing_status = "transcribing"
        record.updated_at = _now()


def _mark_audio_turn_transcript_ready(
    audio_turn_id: str,
    transcript_text: str,
    transcript_confidence: float | None,
) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        record.processing_status = "transcript_ready"
        record.transcript_text = transcript_text
        record.transcript_confidence = transcript_confidence
        record.error_code = None
        record.error_message = None
        record.updated_at = _now()


def _mark_audio_turn_analyzing(
    audio_turn_id: str,
    *,
    normalized_wav_uri: str | None = None,
    duration_ms: int | None = None,
) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        record.processing_status = "analyzing"
        if normalized_wav_uri:
            record.normalized_wav_uri = normalized_wav_uri
        if duration_ms is not None:
            record.duration_ms = duration_ms
        record.error_code = None
        record.error_message = None
        record.updated_at = _now()


def _complete_audio_turn(
    audio_turn_id: str,
    transcript_text: str,
    transcript_confidence: float | None,
    normalized_wav_uri: str | None,
    duration_ms: int | None = None,
) -> None:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if record is None:
            return
        record.processing_status = "completed"
        record.transcript_text = transcript_text
        record.transcript_confidence = transcript_confidence
        record.normalized_wav_uri = normalized_wav_uri
        if duration_ms is not None:
            record.duration_ms = duration_ms
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


def _run_transcription_job(
    audio_turn_id: str,
    multimodal_session_id: str,
    acting_user_id: str | None,
    flow_run_id: str,
    origin_flow_type: str | None,
    turn_id: str,
    stage_id: str,
    question_key: str,
    original_audio_uri: str,
    normalized_wav_object_key: str,
    source_path: Path,
    source_mime_type: str,
    source_filename: str | None,
    captured_at: datetime | None,
) -> None:
    try:
        _mark_audio_turn_transcribing(audio_turn_id)
        wav_path = source_path.parent / "transcription.wav"
        convert_to_wav(source_path, wav_path)
        actual_duration_ms = get_wav_duration_ms(wav_path)
        if actual_duration_ms > get_settings()["upload_max_duration_ms"]:
            raise MultimodalServiceError(
                "audio duration exceeds limit",
                code=4008,
                status_code=413,
            )
        asr_result = get_asr_runtime().transcribe(wav_path)
        transcript_text = str(asr_result.transcript_text or "").strip()
        if not transcript_text:
            trimmed_wav_path = source_path.parent / "transcription.trimmed.wav"
            try:
                trim_leading_silence(wav_path, trimmed_wav_path)
                trimmed_duration_ms = get_wav_duration_ms(trimmed_wav_path)
                if 0 < trimmed_duration_ms < actual_duration_ms:
                    logger.info(
                        "Retrying Dolphin ASR with leading-silence-trimmed wav for audio turn %s (%sms -> %sms).",
                        audio_turn_id,
                        actual_duration_ms,
                        trimmed_duration_ms,
                    )
                    trimmed_result = get_asr_runtime().transcribe(trimmed_wav_path)
                    trimmed_text = str(trimmed_result.transcript_text or "").strip()
                    if trimmed_text:
                        asr_result = trimmed_result
                        transcript_text = trimmed_text
                else:
                    logger.info(
                        "Skipping trimmed-wav ASR retry for audio turn %s because trimming did not shorten the clip (%sms -> %sms).",
                        audio_turn_id,
                        actual_duration_ms,
                        trimmed_duration_ms,
                    )
            except AudioProcessingError as exc:
                logger.warning(
                    "Failed to prepare leading-silence-trimmed wav for audio turn %s: %s",
                    audio_turn_id,
                    exc.message,
                )
        if not transcript_text:
            raise DolphinAsrError(
                "dolphin did not return transcript text",
                error_code="TRANSCRIPTION_FAILED",
            )
        _mark_audio_turn_transcript_ready(
            audio_turn_id,
            transcript_text,
            asr_result.transcript_confidence,
        )

        normalized_wav_bytes = wav_path.read_bytes()
        normalized_wav_uri = upload_audio_object(
            object_key=normalized_wav_object_key,
            file_bytes=normalized_wav_bytes,
            content_type="audio/wav",
        )
        _mark_audio_turn_analyzing(
            audio_turn_id,
            normalized_wav_uri=normalized_wav_uri,
            duration_ms=actual_duration_ms,
        )

        result = process_audio_turn(
            multimodal_session_id,
            payload=SubmitAudioTurnRequest(
                turn_id=turn_id,
                flow_run_id=flow_run_id,
                origin_flow_type=origin_flow_type,
                question_key=question_key,
                stage_id=stage_id,
                original_audio_uri=original_audio_uri,
                original_mime_type=source_mime_type,
                source_filename=source_filename or source_path.name,
                transcript_text=transcript_text,
                normalized_wav_uri=normalized_wav_uri,
                captured_at=captured_at or _now(),
                frame_id=audio_turn_id,
            ),
            audio_emotion_wav_path=wav_path,
            acting_user_id=acting_user_id,
        )
        _complete_audio_turn(
            audio_turn_id=audio_turn_id,
            transcript_text=transcript_text,
            transcript_confidence=asr_result.transcript_confidence,
            normalized_wav_uri=str(
                result.get("normalized_wav_uri") or normalized_wav_uri
            ),
            duration_ms=actual_duration_ms,
        )
    except MultimodalServiceError as exc:
        _fail_audio_turn(audio_turn_id, f"STORE_{exc.code}", exc.message)
    except SessionPipelineError as exc:
        _fail_audio_turn(audio_turn_id, f"PIPELINE_{exc.code}", exc.message)
    except DolphinAsrError as exc:
        _fail_audio_turn(audio_turn_id, exc.error_code, exc.message)
    except Exception as exc:
        _fail_audio_turn(audio_turn_id, "TRANSCRIPTION_FAILED", str(exc))
    finally:
        cleanup_processing_directory(audio_turn_id)
        _remove_active_future(audio_turn_id)


def _submit_transcription_job(
    audio_turn_id: str,
    multimodal_session_id: str,
    acting_user_id: str | None,
    flow_run_id: str,
    origin_flow_type: str | None,
    turn_id: str,
    stage_id: str,
    question_key: str,
    original_audio_uri: str,
    normalized_wav_object_key: str,
    source_path: Path,
    source_mime_type: str,
    source_filename: str | None,
    captured_at: datetime | None,
) -> Future:
    future = _TRANSCRIPTION_EXECUTOR.submit(
        _run_transcription_job,
        audio_turn_id,
        multimodal_session_id,
        acting_user_id,
        flow_run_id,
        origin_flow_type,
        turn_id,
        stage_id,
        question_key,
        original_audio_uri,
        normalized_wav_object_key,
        source_path,
        source_mime_type,
        source_filename,
        captured_at,
    )
    with _ACTIVE_TRANSCRIPTION_LOCK:
        _ACTIVE_TRANSCRIPTION_FUTURES[audio_turn_id] = future
    return future


def create_or_get_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    acting_user_id: str | None,
) -> dict:
    if acting_user_id and payload.user_id and payload.user_id != acting_user_id:
        raise MultimodalServiceError(
            "multimodal session user mismatch",
            code=4032,
            status_code=403,
        )
    effective_user_id = acting_user_id or payload.user_id
    stage_context = (
        payload.stage_context.model_dump() if payload.stage_context else {}
    )
    enabled_modalities = _default_modalities(payload.enabled_modalities)

    with get_db_session() as db_session:
        record = create_or_reuse_session_record(
            db_session,
            payload=payload,
            effective_user_id=effective_user_id,
            stage_context=stage_context,
            enabled_modalities=enabled_modalities,
            now_factory=_now,
            create_status="ready",
            status_on_update="ready",
            fallback_flow_run_id_factory=lambda _session_id: str(uuid.uuid4()),
        )
        return _serialize_session(record)


def get_audio_turn(
    multimodal_session_id: str,
    audio_turn_id: str,
    *,
    acting_user_id: str | None,
) -> dict:
    with get_db_session() as db_session:
        record = db_session.get(MultimodalAudioTurn, audio_turn_id)
        if not record or record.multimodal_session_id != multimodal_session_id:
            raise MultimodalServiceError(
                "audio turn not found",
                code=4042,
                status_code=404,
            )
        session_record = db_session.get(MultimodalSession, multimodal_session_id)
        if session_record is None:
            raise MultimodalServiceError(
                "multimodal session not found",
                code=4041,
                status_code=404,
            )
        _ensure_store_session_access(session_record, acting_user_id)
        return _serialize_audio_turn(record)


async def create_audio_turn(
    multimodal_session_id: str,
    flow_run_id: str,
    origin_flow_type: str | None,
    question_key: str,
    stage_id: str,
    node_id: str,
    duration_ms: int | None,
    response_started_at: datetime | None,
    response_completed_at: datetime | None,
    mime_type: str,
    turn_id: str | None,
    audio_file: UploadFile,
    acting_user_id: str | None,
) -> dict:
    _validate_audio_turn_fields(
        flow_run_id=flow_run_id,
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
        _ensure_store_session_access(session_record, acting_user_id)
        if not session_allows_flow_run(session_record, flow_run_id):
            raise MultimodalServiceError(
                "flow run mismatch",
                code=4091,
                status_code=409,
            )
        resolved_origin_flow_type = (
            str(origin_flow_type or "").strip()
            or str(getattr(session_record, "flow_type", None) or "").strip()
            or "consultation"
        )
        effective_acting_user_id = str(acting_user_id or session_record.user_id or "").strip() or None

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
    effective_turn_id = turn_id or audio_turn_id
    processing_dir = ensure_processing_directory(audio_turn_id)
    source_path = processing_dir / f"source{suffix}"

    try:
        source_path = write_source_audio_file(processing_dir, suffix, file_bytes)
        if (
            duration_ms is not None
            and duration_ms > settings["upload_max_duration_ms"]
        ):
            raise MultimodalServiceError(
                "audio duration exceeds limit",
                code=4008,
                status_code=413,
            )

        object_key = _build_audio_object_key(
            flow_run_id=flow_run_id,
            question_key=question_key,
            audio_turn_id=audio_turn_id,
            suffix=suffix,
        )
        audio_uri = upload_audio_object(
            object_key=object_key,
            file_bytes=file_bytes,
            content_type=normalized_mime_type,
        )
        normalized_wav_object_key = _build_normalized_wav_object_key(
            flow_run_id=flow_run_id,
            question_key=question_key,
            effective_turn_id=effective_turn_id,
        )

        now = _now()
        with get_db_session() as db_session:
            record = MultimodalAudioTurn(
                id=audio_turn_id,
                multimodal_session_id=multimodal_session_id,
                flow_run_id=flow_run_id,
                origin_flow_type=resolved_origin_flow_type,
                turn_id=effective_turn_id,
                stage_id=stage_id,
                node_id=node_id,
                question_key=question_key,
                audio_uri=audio_uri,
                normalized_wav_uri=None,
                storage_provider="minio",
                storage_object_key=object_key,
                source_filename=audio_file.filename,
                mime_type=normalized_mime_type,
                file_size_bytes=len(file_bytes),
                duration_ms=duration_ms,
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

        future = _submit_transcription_job(
            audio_turn_id,
            multimodal_session_id,
            effective_acting_user_id,
            flow_run_id,
            resolved_origin_flow_type,
            effective_turn_id,
            stage_id,
            question_key,
            audio_uri,
            normalized_wav_object_key,
            source_path,
            normalized_mime_type,
            audio_file.filename,
            response_completed_at or response_started_at,
        )
        try:
            _mark_audio_turn_transcribing(audio_turn_id)
            timeout_seconds = settings["asr_sync_timeout_ms"] / 1000
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout_seconds
            while True:
                current_turn = get_audio_turn(
                    multimodal_session_id,
                    audio_turn_id,
                    acting_user_id=acting_user_id,
                )
                if current_turn["processing_status"] in {
                    "transcript_ready",
                    "analyzing",
                    "completed",
                    "failed",
                }:
                    return current_turn
                if loop.time() >= deadline:
                    return current_turn
                await asyncio.sleep(0.2)
        except MultimodalServiceError:
            future.cancel()
            cleanup_processing_directory(audio_turn_id)
            raise
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
                        [
                            "uploaded",
                            "transcribing",
                            "transcript_ready",
                            "analyzing",
                        ]
                    )
                )
            ).scalars()
        ]

    for stale_id in stale_ids:
        _update_audio_turn_for_restart_failure(stale_id)


def shutdown_transcription_executor() -> None:
    _TRANSCRIPTION_EXECUTOR.shutdown(wait=False, cancel_futures=False)
