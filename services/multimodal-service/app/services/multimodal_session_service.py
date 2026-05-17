from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.database import get_db_session
from app.models import (
    MultimodalCapture,
    MultimodalInferenceResult,
    MultimodalSession,
    MultimodalTurnBundle,
)
from app.schemas import (
    AudioEmotionInferRequest,
    CreateMultimodalSessionRequest,
    FrameEmotionInferRequest,
    SubmitAudioTurnRequest,
    SubmitFrameCaptureRequest,
    TextEmotionInferRequest,
    WarmupMultimodalSessionRequest,
)
from app.services.non_eeg_inference import (
    infer_audio_emotion,
    infer_face_emotion,
    infer_pose_emotion,
    infer_text_emotion,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MultimodalServiceError(Exception):
    message: str
    code: int
    status_code: int


def _ensure_session_access(session: MultimodalSession, acting_user_id: str | None) -> None:
    if acting_user_id and session.user_id != acting_user_id:
        raise MultimodalServiceError("multimodal session access denied", 4031, 403)


def _normalize_modalities(modalities: list[str]) -> list[str]:
    valid = {"text", "audio", "face", "pose"}
    normalized: list[str] = []
    for item in modalities:
        key = str(item).strip().lower()
        if key in valid and key not in normalized:
            normalized.append(key)
    return normalized or ["text", "audio", "face", "pose"]


def _snapshot(session: MultimodalSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "owner_session_id": session.owner_session_id,
        "status": session.status,
        "enabled_modalities": list(session.enabled_modalities or []),
        "latest_live_payload": dict(session.latest_live_payload or {}),
        "session_summary_payload": session.session_summary_payload,
        "notes": session.notes,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "warmed_up_at": session.warmed_up_at,
        "completed_at": session.completed_at,
    }


def _extract_result_or_raise(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("code") != 0:
        raise MultimodalServiceError(
            str(response.get("message") or "model inference failed"),
            int(response.get("code") or 5001),
            400 if int(response.get("code") or 5001) < 5000 else 500,
        )
    data = response.get("data") or {}
    result = data.get("result")
    if not isinstance(result, dict):
        raise MultimodalServiceError("model inference returned empty result", 5003, 500)
    return result


def create_multimodal_session(
    payload: CreateMultimodalSessionRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    if acting_user_id and payload.user_id != acting_user_id:
        raise MultimodalServiceError("multimodal session user mismatch", 4032, 403)

    now = _utcnow()
    session = MultimodalSession(
        user_id=payload.user_id,
        owner_session_id=payload.owner_session_id,
        status="created",
        enabled_modalities=_normalize_modalities(payload.enabled_modalities),
        latest_live_payload={},
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    with get_db_session() as db_session:
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)
        return _snapshot(session)


def get_multimodal_session(session_id: str, acting_user_id: str | None = None) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        return _snapshot(session)


def warmup_multimodal_session(
    session_id: str,
    payload: WarmupMultimodalSessionRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    from app.services.non_eeg_runtime import runtime_store

    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        modalities = _normalize_modalities(payload.modalities)
        if "text" in modalities:
            runtime_store.get_text_engine()
        if "audio" in modalities:
            runtime_store.get_audio_engine()
        if "face" in modalities:
            runtime_store.get_face_engine()
        if "pose" in modalities:
            runtime_store.get_pose_engine(session.id)

        now = _utcnow()
        session.status = "warm"
        session.warmed_up_at = now
        session.updated_at = now
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)
        return _snapshot(session)


def _record_capture(
    db_session,
    *,
    session_id: str,
    consultation_turn_id: str | None,
    modality: str,
    capture_kind: str,
    source_ref_id: str | None,
    capture_payload: dict[str, Any],
    captured_at: datetime | None,
) -> None:
    db_session.add(
        MultimodalCapture(
            session_id=session_id,
            consultation_turn_id=consultation_turn_id,
            modality=modality,
            capture_kind=capture_kind,
            source_ref_id=source_ref_id,
            storage_uri=None,
            capture_payload=capture_payload,
            captured_at=captured_at,
            created_at=_utcnow(),
        )
    )


def _record_inference_result(
    db_session,
    *,
    session_id: str,
    consultation_turn_id: str | None,
    modality: str,
    source_kind: str,
    source_ref_id: str | None,
    inference_payload: dict[str, Any],
    captured_at: datetime | None,
) -> None:
    db_session.add(
        MultimodalInferenceResult(
            session_id=session_id,
            consultation_turn_id=consultation_turn_id,
            modality=modality,
            source_kind=source_kind,
            source_ref_id=source_ref_id,
            inference_payload=inference_payload,
            captured_at=captured_at,
            created_at=_utcnow(),
        )
    )


def _refresh_live_payload(session: MultimodalSession, *results: dict[str, Any]) -> None:
    live_payload = dict(session.latest_live_payload or {})
    for result in results:
        modality = str(result.get("modality") or "").strip().lower()
        if modality:
            live_payload[modality] = result
    session.latest_live_payload = live_payload
    session.updated_at = _utcnow()
    if session.status == "created":
        session.status = "active"


def _build_turn_bundle_payload(db_session, session_id: str, consultation_turn_id: str) -> dict[str, Any]:
    rows = db_session.execute(
        select(MultimodalInferenceResult)
        .where(
            MultimodalInferenceResult.session_id == session_id,
            MultimodalInferenceResult.consultation_turn_id == consultation_turn_id,
        )
        .order_by(MultimodalInferenceResult.created_at.asc())
    ).scalars()

    results_by_modality: dict[str, dict[str, Any]] = {}
    for row in rows:
        results_by_modality[row.modality] = row.inference_payload

    return {
        "session_id": session_id,
        "consultation_turn_id": consultation_turn_id,
        "modalities": sorted(results_by_modality.keys()),
        "results": results_by_modality,
        "updated_at": _utcnow().isoformat(),
    }


def _upsert_turn_bundle(db_session, session_id: str, consultation_turn_id: str) -> dict[str, Any]:
    bundle_payload = _build_turn_bundle_payload(db_session, session_id, consultation_turn_id)
    row = db_session.execute(
        select(MultimodalTurnBundle).where(
            MultimodalTurnBundle.session_id == session_id,
            MultimodalTurnBundle.consultation_turn_id == consultation_turn_id,
        )
    ).scalar_one_or_none()

    now = _utcnow()
    if row is None:
        row = MultimodalTurnBundle(
            session_id=session_id,
            consultation_turn_id=consultation_turn_id,
            bundle_payload=bundle_payload,
            created_at=now,
            updated_at=now,
        )
        db_session.add(row)
    else:
        row.bundle_payload = bundle_payload
        row.updated_at = now
        db_session.add(row)
    return bundle_payload


def submit_audio_turn(
    session_id: str,
    payload: SubmitAudioTurnRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="audio",
            capture_kind="audio_turn",
            source_ref_id=payload.frame_id,
            capture_payload={
                "audio_format": payload.audio_format,
                "sampling_rate": payload.sampling_rate,
                "audio_base64_length": len(payload.audio_base64),
                "has_transcript_text": bool(payload.transcript_text and payload.transcript_text.strip()),
            },
            captured_at=payload.captured_at,
        )

        audio_result = _extract_result_or_raise(
            infer_audio_emotion(
                AudioEmotionInferRequest(
                    audio_base64=payload.audio_base64,
                    audio_format=payload.audio_format,
                    sampling_rate=payload.sampling_rate,
                    session_id=session.id,
                    frame_id=payload.frame_id,
                    timestamp=payload.captured_at.isoformat() if payload.captured_at else None,
                )
            )
        )
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="audio",
            source_kind="audio_turn",
            source_ref_id=payload.frame_id,
            inference_payload=audio_result,
            captured_at=payload.captured_at,
        )

        text_result: dict[str, Any] | None = None
        if payload.transcript_text and payload.transcript_text.strip():
            text_result = _extract_result_or_raise(
                infer_text_emotion(
                    TextEmotionInferRequest(
                        text=payload.transcript_text.strip(),
                        session_id=session.id,
                        frame_id=payload.frame_id,
                        timestamp=payload.captured_at.isoformat() if payload.captured_at else None,
                    )
                )
            )
            _record_inference_result(
                db_session,
                session_id=session.id,
                consultation_turn_id=payload.consultation_turn_id,
                modality="text",
                source_kind="transcript_text",
                source_ref_id=payload.frame_id,
                inference_payload=text_result,
                captured_at=payload.captured_at,
            )

        _refresh_live_payload(session, *(result for result in [audio_result, text_result] if result is not None))
        db_session.add(session)
        db_session.flush()
        bundle_payload = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        db_session.refresh(session)
        return {
            "multimodal_session": _snapshot(session),
            "turn_bundle": bundle_payload,
        }


def submit_face_capture(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="face",
            capture_kind="frame",
            source_ref_id=payload.frame_id,
            capture_payload={
                "image_format": payload.image_format,
                "image_base64_length": len(payload.image_base64),
            },
            captured_at=payload.captured_at,
        )

        face_result = _extract_result_or_raise(
            infer_face_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.image_base64,
                    image_format=payload.image_format,
                    session_id=session.id,
                    frame_id=payload.frame_id,
                    timestamp=payload.captured_at.isoformat() if payload.captured_at else None,
                )
            )
        )
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="face",
            source_kind="frame",
            source_ref_id=payload.frame_id,
            inference_payload=face_result,
            captured_at=payload.captured_at,
        )

        _refresh_live_payload(session, face_result)
        db_session.add(session)
        turn_bundle = None
        if payload.consultation_turn_id:
            db_session.flush()
            turn_bundle = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        db_session.refresh(session)
        return {
            "multimodal_session": _snapshot(session),
            "result": face_result,
            "turn_bundle": turn_bundle,
        }


def submit_pose_capture(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="pose",
            capture_kind="frame",
            source_ref_id=payload.frame_id,
            capture_payload={
                "image_format": payload.image_format,
                "image_base64_length": len(payload.image_base64),
            },
            captured_at=payload.captured_at,
        )

        pose_result = _extract_result_or_raise(
            infer_pose_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.image_base64,
                    image_format=payload.image_format,
                    session_id=session.id,
                    frame_id=payload.frame_id,
                    timestamp=payload.captured_at.isoformat() if payload.captured_at else None,
                )
            )
        )
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="pose",
            source_kind="frame",
            source_ref_id=payload.frame_id,
            inference_payload=pose_result,
            captured_at=payload.captured_at,
        )

        _refresh_live_payload(session, pose_result)
        db_session.add(session)
        turn_bundle = None
        if payload.consultation_turn_id:
            db_session.flush()
            turn_bundle = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        db_session.refresh(session)
        return {
            "multimodal_session": _snapshot(session),
            "result": pose_result,
            "turn_bundle": turn_bundle,
        }


def get_multimodal_live(session_id: str, acting_user_id: str | None = None) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        return {
            "session_id": session.id,
            "owner_session_id": session.owner_session_id,
            "live": dict(session.latest_live_payload or {}),
            "updated_at": session.updated_at,
        }


def get_multimodal_turn_bundle(
    session_id: str,
    consultation_turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        row = db_session.execute(
            select(MultimodalTurnBundle).where(
                MultimodalTurnBundle.session_id == session_id,
                MultimodalTurnBundle.consultation_turn_id == consultation_turn_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise MultimodalServiceError("multimodal turn bundle not found", 4042, 404)
        return row.bundle_payload
