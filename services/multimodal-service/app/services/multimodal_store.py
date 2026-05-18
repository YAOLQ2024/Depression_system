from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalAudioTurn, MultimodalSession


class MultimodalServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_session(record: MultimodalSession) -> dict:
    return {
        "session_id": record.id,
        "consultation_session_id": record.consultation_session_id,
        "user_id": record.user_id,
        "workflow_id": record.workflow_id,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _serialize_audio_turn(record: MultimodalAudioTurn) -> dict:
    return {
        "audio_turn_id": record.id,
        "multimodal_session_id": record.multimodal_session_id,
        "consultation_session_id": record.consultation_session_id,
        "question_key": record.question_key,
        "prompt_key": record.prompt_key,
        "audio_uri": record.audio_uri,
        "storage_provider": record.storage_provider,
        "stored_relative_path": record.stored_relative_path,
        "source_filename": record.source_filename,
        "mime_type": record.mime_type,
        "file_size_bytes": record.file_size_bytes,
        "duration_ms": record.duration_ms,
        "processing_status": record.processing_status,
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


def _ensure_runtime_assets_dir() -> Path:
    runtime_assets_dir = get_settings()["runtime_assets_dir"]
    runtime_assets_dir.mkdir(parents=True, exist_ok=True)
    return runtime_assets_dir


def _resolve_upload_suffix(audio_file: UploadFile) -> str:
    raw_name = Path(audio_file.filename or "response").name
    if Path(raw_name).suffix:
        return Path(raw_name).suffix
    if audio_file.content_type == "audio/mp4":
        return ".mp4"
    if audio_file.content_type == "audio/ogg":
        return ".ogg"
    return ".webm"


def create_or_get_multimodal_session(
    consultation_session_id: str,
    workflow_id: str | None,
    acting_user_id: str | None,
) -> dict:
    with get_db_session() as db_session:
        existing = db_session.execute(
            select(MultimodalSession).where(
                MultimodalSession.consultation_session_id
                == consultation_session_id
            )
        ).scalar_one_or_none()
        if existing:
            if workflow_id and not existing.workflow_id:
                existing.workflow_id = workflow_id
                existing.updated_at = _now()
                db_session.flush()
                db_session.refresh(existing)
            return _serialize_session(existing)

        now = _now()
        record = MultimodalSession(
            id=str(uuid.uuid4()),
            consultation_session_id=consultation_session_id,
            user_id=acting_user_id,
            workflow_id=workflow_id,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db_session.add(record)
        db_session.flush()
        db_session.refresh(record)
        return _serialize_session(record)


async def create_audio_turn(
    multimodal_session_id: str,
    consultation_session_id: str,
    question_key: str,
    prompt_key: str | None,
    duration_ms: int | None,
    response_started_at: datetime | None,
    response_completed_at: datetime | None,
    audio_file: UploadFile,
) -> dict:
    if not consultation_session_id:
        raise MultimodalServiceError(
            "consultation_session_id is required",
            code=4001,
        )
    if not question_key:
        raise MultimodalServiceError("question_key is required", code=4002)

    with get_db_session() as db_session:
        session_record = db_session.get(MultimodalSession, multimodal_session_id)
        if not session_record:
            raise MultimodalServiceError(
                "multimodal session not found",
                code=4041,
                status_code=404,
            )
        if (
            session_record.consultation_session_id
            != consultation_session_id
        ):
            raise MultimodalServiceError(
                "consultation session mismatch",
                code=4091,
                status_code=409,
            )

        file_bytes = await audio_file.read()
        if not file_bytes:
            raise MultimodalServiceError("audio_file is empty", code=4003)

        audio_turn_id = str(uuid.uuid4())
        suffix = _resolve_upload_suffix(audio_file)
        relative_path = (
            Path("uploads")
            / "audio"
            / session_record.id
            / question_key
            / f"{audio_turn_id}{suffix}"
        )
        runtime_assets_dir = _ensure_runtime_assets_dir()
        target_path = runtime_assets_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(file_bytes)

        now = _now()
        audio_uri = (
            f"multimodal://sessions/{session_record.id}/audio-turns/"
            f"{audio_turn_id}"
        )
        record = MultimodalAudioTurn(
            id=audio_turn_id,
            multimodal_session_id=session_record.id,
            consultation_session_id=consultation_session_id,
            question_key=question_key,
            prompt_key=prompt_key,
            audio_uri=audio_uri,
            storage_provider="runtime-assets-placeholder",
            stored_relative_path=relative_path.as_posix(),
            source_filename=audio_file.filename,
            mime_type=audio_file.content_type,
            file_size_bytes=len(file_bytes),
            duration_ms=duration_ms,
            processing_status="uploaded_pending_transcription",
            response_started_at=response_started_at,
            response_completed_at=response_completed_at,
            created_at=now,
            updated_at=now,
        )
        db_session.add(record)
        session_record.updated_at = now
        db_session.flush()
        db_session.refresh(record)
        return _serialize_audio_turn(record)
