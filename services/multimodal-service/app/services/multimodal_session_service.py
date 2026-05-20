from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

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
from app.services.asr_runtime import DolphinAsrError, get_asr_runtime
from app.services.non_eeg_inference import (
    infer_audio_emotion,
    infer_audio_emotion_from_wav_path,
    infer_face_emotion,
    infer_pose_emotion,
    infer_text_emotion,
)
from app.services.audio_processing import (
    AudioProcessingError,
    cleanup_processing_directory,
    convert_to_wav,
    ensure_processing_directory,
    write_source_audio_file,
)
from app.services.object_storage import (
    download_object_bytes,
    parse_s3_uri,
    upload_object_to_bucket,
)


NEGATIVE_TERM_CANDIDATES = [
    "失眠",
    "睡不着",
    "焦虑",
    "难受",
    "压抑",
    "痛苦",
    "绝望",
    "低落",
    "烦躁",
    "紧张",
]

_AUDIO_TURN_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="multimodal-audio-turn",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _copy_labels(labels: Sequence[dict[str, Any]] | None, *, limit: int = 3) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for item in labels or []:
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        copied.append({"label": label, "score": float(item.get("score") or 0.0)})
        if len(copied) >= limit:
            break
    return copied


def _top_labels_from_pairs(pairs: Iterable[tuple[str, float]], *, limit: int = 3) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for label, score in sorted(pairs, key=lambda item: item[1], reverse=True):
        normalized = str(label or "").strip()
        if not normalized:
            continue
        result.append({"label": normalized, "score": float(score)})
        if len(result) >= limit:
            break
    return result


def _top_labels_from_scores(scores: dict[str, Any] | None, *, limit: int = 3) -> list[dict[str, Any]]:
    if not scores:
        return []
    pairs = [(str(label), float(score or 0.0)) for label, score in scores.items()]
    return _top_labels_from_pairs(pairs, limit=limit)


def _extract_negative_terms(text: str | None) -> list[str]:
    if not text:
        return []
    matched = [term for term in NEGATIVE_TERM_CANDIDATES if term in text]
    return list(dict.fromkeys(matched))


def _build_pending_live_modality(modality: str) -> dict[str, Any]:
    base = {
        "status": "pending",
        "primary_label": None,
        "primary_score": None,
    }
    if modality in {"speech", "text"}:
        base["top_3_labels"] = []
    if modality == "text":
        base["negative_terms"] = []
    if modality in {"face", "pose"}:
        base["latest_capture_at"] = None
    return base


def _bool_ratio(payloads: Sequence[dict[str, Any]], key: str) -> float:
    if not payloads:
        return 0.0
    positive = 0
    for payload in payloads:
        quality_flags = payload.get("quality_flags") or {}
        if bool(quality_flags.get(key)):
            positive += 1
    return round(positive / len(payloads), 4)


def _summarize_frame_payloads(
    modality: str,
    payloads: Sequence[dict[str, Any]],
    *,
    summary_type: str,
) -> dict[str, Any]:
    if not payloads:
        if modality == "face":
            return {
                "summary_type": summary_type,
                "primary_label": None,
                "primary_score": None,
                "top_3_labels": [],
                "sample_count": 0,
                "quality_flags": {"no_face_ratio": 0.0, "blur_ratio": 0.0, "low_light_ratio": 0.0},
            }
        return {
            "summary_type": summary_type,
            "primary_label": None,
            "primary_score": None,
            "top_3_labels": [],
            "sample_count": 0,
            "quality_flags": {"no_pose_ratio": 0.0, "body_cutoff_ratio": 0.0, "motion_blur_ratio": 0.0},
        }

    aggregated_scores: Counter[str] = Counter()
    effective_count = 0
    for payload in payloads:
        labels = _copy_labels(payload.get("top_3_labels"))
        if labels:
            effective_count += 1
        for label in labels:
            aggregated_scores[label["label"]] += float(label["score"])

    top_3_labels: list[dict[str, Any]] = []
    primary_label: str | None = None
    primary_score: float | None = None
    if aggregated_scores:
        divisor = max(effective_count, 1)
        normalized_pairs = [
            (label, score / divisor)
            for label, score in aggregated_scores.items()
        ]
        top_3_labels = _top_labels_from_pairs(normalized_pairs, limit=3)
        if top_3_labels:
            primary_label = top_3_labels[0]["label"]
            primary_score = top_3_labels[0]["score"]

    if modality == "face":
        quality_flags = {
            "no_face_ratio": _bool_ratio(payloads, "no_face"),
            "blur_ratio": _bool_ratio(payloads, "blur"),
            "low_light_ratio": _bool_ratio(payloads, "low_light"),
        }
    else:
        quality_flags = {
            "no_pose_ratio": _bool_ratio(payloads, "no_pose"),
            "body_cutoff_ratio": _bool_ratio(payloads, "body_cutoff"),
            "motion_blur_ratio": _bool_ratio(payloads, "motion_blur"),
        }

    return {
        "summary_type": summary_type,
        "primary_label": primary_label,
        "primary_score": primary_score,
        "top_3_labels": top_3_labels,
        "sample_count": len(payloads),
        "quality_flags": quality_flags,
    }


def _normalize_speech_result(raw_result: dict[str, Any], payload: SubmitAudioTurnRequest) -> dict[str, Any]:
    top_3_labels = _copy_labels(
        [
            {"label": label, "score": score}
            for label, score in (raw_result.get("extra") or {}).get("topk", [])[:3]
        ]
    )
    return {
        "modality": "speech",
        "status": "ready",
        "question_key": payload.question_key,
        "consultation_session_id": payload.consultation_session_id,
        "turn_id": payload.consultation_turn_id,
        "primary_label": raw_result.get("label"),
        "primary_score": float(raw_result.get("score") or 0.0),
        "top_3_labels": top_3_labels,
        "audio_uri": payload.original_audio_uri,
        "original_audio_uri": payload.original_audio_uri,
        "normalized_wav_uri": payload.normalized_wav_uri,
        "captured_at": _isoformat(payload.captured_at),
    }


def _normalize_text_result(raw_result: dict[str, Any], payload: SubmitAudioTurnRequest) -> dict[str, Any]:
    transcript_text = (payload.transcript_text or "").strip()
    top_3_labels = _copy_labels(
        [
            {"label": label, "score": score}
            for label, score in (raw_result.get("extra") or {}).get("topk", [])[:3]
        ]
    )
    return {
        "modality": "text",
        "status": "ready",
        "question_key": payload.question_key,
        "consultation_session_id": payload.consultation_session_id,
        "turn_id": payload.consultation_turn_id,
        "primary_label": raw_result.get("label"),
        "primary_score": float(raw_result.get("score") or 0.0),
        "top_3_labels": top_3_labels,
        "negative_terms": _extract_negative_terms(transcript_text),
        "transcript_text": transcript_text,
        "captured_at": _isoformat(payload.captured_at),
    }


def _normalize_face_result(raw_result: dict[str, Any], payload: SubmitFrameCaptureRequest) -> dict[str, Any]:
    status = str(raw_result.get("status") or "error").lower()
    processing_status = "completed" if status in {"ok", "no_face"} else "processing"
    scores = raw_result.get("scores") or {}
    return {
        "modality": "face",
        "status": "ready" if processing_status == "completed" else "pending",
        "processing_status": processing_status,
        "question_key": payload.question_key,
        "consultation_session_id": payload.consultation_session_id,
        "turn_id": payload.consultation_turn_id,
        "primary_label": raw_result.get("dominant_emotion_zh"),
        "primary_score": float(raw_result.get("confidence") or 0.0),
        "top_3_labels": _top_labels_from_scores(scores, limit=3),
        "quality_flags": {
            "no_face": status == "no_face",
            "blur": False,
            "low_light": False,
        },
        "capture_started_at": _isoformat(payload.capture_started_at),
        "capture_ended_at": _isoformat(payload.capture_ended_at),
        "frame_index": payload.frame_index,
    }


def _normalize_pose_result(raw_result: dict[str, Any], payload: SubmitFrameCaptureRequest) -> dict[str, Any]:
    label = str(raw_result.get("label") or "").strip()
    is_collecting = label == "collecting"
    is_no_pose = str(raw_result.get("status") or "").lower() == "no_pose"
    confidences = (raw_result.get("extra") or {}).get("confidences") or {}
    return {
        "modality": "pose",
        "status": "pending" if is_collecting else "ready",
        "processing_status": "processing" if is_collecting else "completed",
        "question_key": payload.question_key,
        "consultation_session_id": payload.consultation_session_id,
        "turn_id": payload.consultation_turn_id,
        "primary_label": None if is_collecting else label,
        "primary_score": None if is_collecting else float(raw_result.get("score") or 0.0),
        "top_3_labels": [] if is_collecting else _top_labels_from_scores(confidences, limit=3),
        "quality_flags": {
            "no_pose": is_no_pose,
            "body_cutoff": False,
            "motion_blur": False,
        },
        "capture_started_at": _isoformat(payload.capture_started_at),
        "capture_ended_at": _isoformat(payload.capture_ended_at),
        "frame_index": payload.frame_index,
    }


@dataclass
class MultimodalServiceError(Exception):
    message: str
    code: int
    status_code: int


@dataclass(slots=True)
class PreparedNormalizedAudio:
    processing_id: str
    normalized_wav_uri: str
    normalized_wav_bytes: bytes
    wav_path: Path


def _resolve_audio_source_suffix(payload: SubmitAudioTurnRequest) -> str:
    if payload.source_filename:
        suffix = Path(payload.source_filename).suffix.lower()
        if suffix:
            return suffix
    if payload.original_mime_type:
        mime = payload.original_mime_type.split(";", 1)[0].strip().lower()
        mime_map = {
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".mp4",
            "audio/mpeg": ".mp3",
        }
        if mime in mime_map:
            return mime_map[mime]
    if payload.original_audio_uri:
        try:
            _, object_key = parse_s3_uri(payload.original_audio_uri)
            suffix = Path(object_key).suffix.lower()
            if suffix:
                return suffix
        except ValueError:
            pass
    return ".webm"


def _build_normalized_wav_object_key(payload: SubmitAudioTurnRequest) -> tuple[str, str]:
    if not payload.original_audio_uri:
        raise MultimodalServiceError(
            "original_audio_uri is required",
            4006,
            422,
        )
    try:
        bucket_name, _ = parse_s3_uri(payload.original_audio_uri)
    except ValueError as exc:
        raise MultimodalServiceError("invalid original_audio_uri", 4007, 422) from exc
    object_key = (
        f"consultation-audio/{payload.consultation_session_id}/"
        f"{payload.consultation_turn_id}/normalized/response.wav"
    )
    return bucket_name, object_key


def _prepare_normalized_audio(
    payload: SubmitAudioTurnRequest,
) -> PreparedNormalizedAudio:
    if not payload.original_audio_uri:
        raise MultimodalServiceError("original_audio_uri is required", 4006, 422)
    source_suffix = _resolve_audio_source_suffix(payload)
    processing_id = f"turn-{payload.consultation_turn_id}"
    processing_dir = ensure_processing_directory(processing_id)
    try:
        source_bytes = download_object_bytes(payload.original_audio_uri)
        source_path = write_source_audio_file(processing_dir, source_suffix, source_bytes)
        wav_path = processing_dir / "normalized.wav"
        convert_to_wav(source_path, wav_path)
        normalized_wav_bytes = wav_path.read_bytes()
        bucket_name, object_key = _build_normalized_wav_object_key(payload)
        normalized_wav_uri = upload_object_to_bucket(
            bucket_name=bucket_name,
            object_key=object_key,
            file_bytes=normalized_wav_bytes,
            content_type="audio/wav",
        )
        return PreparedNormalizedAudio(
            processing_id=processing_id,
            normalized_wav_uri=normalized_wav_uri,
            normalized_wav_bytes=normalized_wav_bytes,
            wav_path=wav_path,
        )
    except AudioProcessingError as exc:
        cleanup_processing_directory(processing_id)
        raise MultimodalServiceError(exc.message, 4004, exc.status_code) from exc


def _materialize_transcription_wav(
    *,
    consultation_turn_id: str,
    audio_base64: str,
    audio_format: str | None,
) -> PreparedNormalizedAudio:
    processing_id = f"turn-asr-{consultation_turn_id}"
    processing_dir = ensure_processing_directory(processing_id)
    source_suffix = f".{(audio_format or 'wav').strip().lower().lstrip('.') or 'wav'}"

    try:
        source_bytes = base64.b64decode(audio_base64)
        source_path = write_source_audio_file(
            processing_dir,
            source_suffix,
            source_bytes,
        )
        wav_path = processing_dir / "transcription.wav"
        if source_suffix == ".wav":
            wav_path.write_bytes(source_bytes)
        else:
            convert_to_wav(source_path, wav_path)
        normalized_wav_bytes = wav_path.read_bytes()
        return PreparedNormalizedAudio(
            processing_id=processing_id,
            normalized_wav_uri="",
            normalized_wav_bytes=normalized_wav_bytes,
            wav_path=wav_path,
        )
    except AudioProcessingError as exc:
        cleanup_processing_directory(processing_id)
        raise MultimodalServiceError(exc.message, 4004, exc.status_code) from exc


def _infer_audio_emotion_payload(
    *,
    session_id: str,
    frame_id: str | None,
    captured_at: datetime,
    audio_base64: str,
    audio_format: str,
    sampling_rate: int | None,
) -> dict[str, Any]:
    return _extract_result_or_raise(
        infer_audio_emotion(
            AudioEmotionInferRequest(
                audio_base64=audio_base64,
                audio_format=audio_format,
                sampling_rate=sampling_rate,
                session_id=session_id,
                frame_id=frame_id,
                timestamp=_isoformat(captured_at),
            )
        )
    )


def _infer_audio_emotion_from_wav_path_payload(
    wav_path: Path,
) -> dict[str, Any]:
    return _extract_result_or_raise(infer_audio_emotion_from_wav_path(wav_path))


def _transcribe_audio_payload(wav_path: Path) -> dict[str, Any]:
    result = get_asr_runtime().transcribe(wav_path)
    return {
        "transcript_text": result.transcript_text.strip(),
        "transcript_confidence": result.transcript_confidence,
        "resolved_device": result.resolved_device,
    }


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


def _stage_context_payload(session: MultimodalSession) -> dict[str, Any]:
    return dict(session.stage_context or {})


def _snapshot(session: MultimodalSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "session_id": session.id,
        "user_id": session.user_id,
        "owner_service": session.owner_service,
        "owner_session_id": session.owner_session_id,
        "status": session.status,
        "stage_context": _stage_context_payload(session),
        "enabled_modalities": list(session.enabled_modalities or []),
        "latest_live_payload": dict(session.latest_live_payload or {}),
        "session_summary_payload": session.session_summary_payload,
        "notes": session.notes,
        "started_at": session.started_at,
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
    if acting_user_id and payload.user_id and payload.user_id != acting_user_id:
        raise MultimodalServiceError("multimodal session user mismatch", 4032, 403)

    effective_user_id = acting_user_id or payload.user_id
    owner_service = payload.owner_service or "consultation-service"
    stage_context = payload.stage_context.model_dump() if payload.stage_context else {}
    now = _utcnow()
    with get_db_session() as db_session:
        existing = db_session.execute(
            select(MultimodalSession).where(
                MultimodalSession.owner_service == owner_service,
                MultimodalSession.owner_session_id == payload.owner_session_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            if acting_user_id:
                _ensure_session_access(existing, acting_user_id)
            existing.user_id = effective_user_id or existing.user_id
            existing.stage_context = stage_context or dict(existing.stage_context or {})
            existing.enabled_modalities = _normalize_modalities(payload.enabled_modalities)
            existing.latest_live_payload = existing.latest_live_payload or {}
            existing.notes = payload.notes if payload.notes is not None else existing.notes
            existing.started_at = existing.started_at or existing.created_at or now
            existing.created_at = existing.created_at or existing.started_at or now
            existing.updated_at = now
            db_session.add(existing)
            db_session.flush()
            db_session.refresh(existing)
            return _snapshot(existing)

        session = MultimodalSession(
            user_id=effective_user_id,
            owner_service=owner_service,
            owner_session_id=payload.owner_session_id,
            stage_context=stage_context,
            status="created",
            enabled_modalities=_normalize_modalities(payload.enabled_modalities),
            latest_live_payload={},
            notes=payload.notes,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
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
            get_asr_runtime().warmup()
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
) -> MultimodalCapture:
    row = MultimodalCapture(
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
    db_session.add(row)
    db_session.flush()
    return row


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
) -> MultimodalInferenceResult:
    row = MultimodalInferenceResult(
        session_id=session_id,
        consultation_turn_id=consultation_turn_id,
        modality=modality,
        source_kind=source_kind,
        source_ref_id=source_ref_id,
        inference_payload=inference_payload,
        captured_at=captured_at,
        created_at=_utcnow(),
    )
    db_session.add(row)
    db_session.flush()
    return row


def _refresh_live_payload(session: MultimodalSession, *results: dict[str, Any]) -> None:
    live_payload = dict(session.latest_live_payload or {})
    for result in results:
        modality = str(result.get("modality") or "").strip().lower()
        if not modality:
            continue
        if modality in {"face", "pose"}:
            live_payload[modality] = {
                "status": result.get("status", "pending"),
                "primary_label": result.get("primary_label"),
                "primary_score": result.get("primary_score"),
                "latest_capture_at": result.get("capture_ended_at"),
            }
        else:
            live_payload[modality] = {
                "status": result.get("status", "pending"),
                "primary_label": result.get("primary_label"),
                "primary_score": result.get("primary_score"),
                "top_3_labels": _copy_labels(result.get("top_3_labels")),
            }
            if modality == "text":
                live_payload[modality]["negative_terms"] = list(result.get("negative_terms") or [])
    session.latest_live_payload = live_payload
    session.updated_at = _utcnow()
    if session.status == "created":
        session.status = "active"


def _load_inference_payloads(
    db_session,
    *,
    session_id: str,
    modality: str,
    consultation_turn_id: str | None = None,
) -> list[dict[str, Any]]:
    statement = select(MultimodalInferenceResult).where(
        MultimodalInferenceResult.session_id == session_id,
        MultimodalInferenceResult.modality == modality,
    )
    if consultation_turn_id is not None:
        statement = statement.where(MultimodalInferenceResult.consultation_turn_id == consultation_turn_id)
    rows = db_session.execute(statement.order_by(MultimodalInferenceResult.created_at.asc())).scalars().all()
    return [dict(row.inference_payload or {}) for row in rows]


def _refresh_session_summary(
    db_session,
    session: MultimodalSession,
    *,
    modalities: Sequence[str] = ("face", "pose"),
) -> None:
    summary_payload = dict(session.session_summary_payload or {})
    for modality in modalities:
        payloads = _load_inference_payloads(db_session, session_id=session.id, modality=modality)
        if modality == "face":
            summary_payload["face_summary"] = _summarize_frame_payloads("face", payloads, summary_type="session_window")
        elif modality == "pose":
            summary_payload["pose_summary"] = _summarize_frame_payloads("pose", payloads, summary_type="session_window")
    session.session_summary_payload = summary_payload


def _resolve_question_key(results_by_modality: dict[str, list[dict[str, Any]]]) -> str | None:
    for modality in ("speech", "text", "face", "pose"):
        rows = results_by_modality.get(modality) or []
        for row in reversed(rows):
            question_key = row.get("question_key")
            if question_key:
                return str(question_key)
    return None


def _build_turn_bundle_payload(db_session, session_id: str, consultation_turn_id: str) -> dict[str, Any]:
    results_by_modality = {
        "speech": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="speech",
            consultation_turn_id=consultation_turn_id,
        ),
        "text": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="text",
            consultation_turn_id=consultation_turn_id,
        ),
        "face": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="face",
            consultation_turn_id=consultation_turn_id,
        ),
        "pose": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="pose",
            consultation_turn_id=consultation_turn_id,
        ),
    }

    latest_speech = results_by_modality["speech"][-1] if results_by_modality["speech"] else None
    latest_text = results_by_modality["text"][-1] if results_by_modality["text"] else None
    face_summary = _summarize_frame_payloads("face", results_by_modality["face"], summary_type="turn_window")
    pose_summary = _summarize_frame_payloads("pose", results_by_modality["pose"], summary_type="turn_window")

    return {
        "turn_id": consultation_turn_id,
        "session_id": session_id,
        "question_key": _resolve_question_key(results_by_modality),
        "generated_at": _isoformat(_utcnow()),
        "speech_features": {
            "primary_label": latest_speech.get("primary_label") if latest_speech else None,
            "primary_score": latest_speech.get("primary_score") if latest_speech else None,
            "top_3_labels": _copy_labels(latest_speech.get("top_3_labels")) if latest_speech else [],
        },
        "text_features": {
            "primary_label": latest_text.get("primary_label") if latest_text else None,
            "primary_score": latest_text.get("primary_score") if latest_text else None,
            "top_3_labels": _copy_labels(latest_text.get("top_3_labels")) if latest_text else [],
            "negative_terms": list(latest_text.get("negative_terms") or []) if latest_text else [],
        },
        "face_features": face_summary,
        "pose_features": pose_summary,
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
    *,
    transcription_wav_path: Path | None = None,
    audio_emotion_wav_path: Path | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        captured_at = payload.captured_at or _utcnow()
        resolved_normalized_wav_uri = payload.normalized_wav_uri
        resolved_audio_base64 = payload.audio_base64
        resolved_audio_format = payload.audio_format
        resolved_sampling_rate = payload.sampling_rate
        prepared_audio: PreparedNormalizedAudio | None = None
        materialized_audio: PreparedNormalizedAudio | None = None
        effective_transcription_wav_path = transcription_wav_path
        effective_audio_emotion_wav_path = audio_emotion_wav_path
        if (
            not resolved_audio_base64
            and effective_transcription_wav_path is None
            and effective_audio_emotion_wav_path is None
        ):
            prepared_audio = _prepare_normalized_audio(payload)
            resolved_normalized_wav_uri = prepared_audio.normalized_wav_uri
            resolved_audio_base64 = base64.b64encode(
                prepared_audio.normalized_wav_bytes
            ).decode(
                "ascii"
            )
            resolved_audio_format = "wav"
            resolved_sampling_rate = 16000
            effective_transcription_wav_path = prepared_audio.wav_path
            effective_audio_emotion_wav_path = prepared_audio.wav_path
        elif resolved_audio_base64 and (
            effective_transcription_wav_path is None
            or effective_audio_emotion_wav_path is None
        ):
            materialized_audio = _materialize_transcription_wav(
                consultation_turn_id=payload.consultation_turn_id,
                audio_base64=resolved_audio_base64,
                audio_format=resolved_audio_format,
            )
            if effective_transcription_wav_path is None:
                effective_transcription_wav_path = materialized_audio.wav_path
            if effective_audio_emotion_wav_path is None:
                effective_audio_emotion_wav_path = materialized_audio.wav_path

        working_payload = payload.model_copy(
            update={
                "audio_base64": resolved_audio_base64,
                "audio_format": resolved_audio_format,
                "sampling_rate": resolved_sampling_rate,
                "normalized_wav_uri": resolved_normalized_wav_uri,
            }
        )
        provided_transcript_text = (
            str(payload.transcript_text or "").strip() or None
        )
        _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="audio",
            capture_kind="audio_turn",
            source_ref_id=payload.frame_id,
            capture_payload={
                "consultation_session_id": payload.consultation_session_id,
                "question_key": payload.question_key,
                "audio_format": resolved_audio_format,
                "audio_uri": payload.original_audio_uri,
                "original_audio_uri": payload.original_audio_uri,
                "normalized_wav_uri": resolved_normalized_wav_uri,
                "sampling_rate": resolved_sampling_rate,
                "audio_base64_length": (
                    len(resolved_audio_base64)
                    if resolved_audio_base64 is not None
                    else None
                ),
                "has_transcript_text": bool(payload.transcript_text and payload.transcript_text.strip()),
            },
            captured_at=captured_at,
        )

        try:
            if effective_audio_emotion_wav_path is not None:
                speech_future = _AUDIO_TURN_EXECUTOR.submit(
                    _infer_audio_emotion_from_wav_path_payload,
                    effective_audio_emotion_wav_path,
                )
            else:
                speech_future = _AUDIO_TURN_EXECUTOR.submit(
                    _infer_audio_emotion_payload,
                    session_id=session.id,
                    frame_id=payload.frame_id,
                    captured_at=captured_at,
                    audio_base64=resolved_audio_base64,
                    audio_format=resolved_audio_format or "wav",
                    sampling_rate=resolved_sampling_rate,
                )
            speech_raw_result = speech_future.result()
            if provided_transcript_text is not None:
                asr_payload = {
                    "transcript_text": provided_transcript_text,
                    "transcript_confidence": None,
                }
            else:
                if effective_transcription_wav_path is None:
                    raise MultimodalServiceError(
                        "transcription audio is not ready",
                        5003,
                        500,
                    )
                asr_future = _AUDIO_TURN_EXECUTOR.submit(
                    _transcribe_audio_payload,
                    effective_transcription_wav_path,
                )
                asr_payload = asr_future.result()
        except DolphinAsrError as exc:
            raise MultimodalServiceError(
                exc.message,
                5032 if exc.error_code == "MODEL_NOT_READY" else 5002,
                503 if exc.error_code == "MODEL_NOT_READY" else 500,
            ) from exc
        finally:
            for prepared in (materialized_audio, prepared_audio):
                if prepared is not None:
                    cleanup_processing_directory(prepared.processing_id)

        final_transcript_text = (
            str(asr_payload.get("transcript_text") or "").strip() or None
        )
        speech_result = _normalize_speech_result(speech_raw_result, working_payload)
        speech_result["transcript_confidence"] = asr_payload.get(
            "transcript_confidence"
        )
        speech_result["asr_provider"] = "dolphin" if final_transcript_text else None
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="speech",
            source_kind="audio_turn",
            source_ref_id=payload.frame_id,
            inference_payload=speech_result,
            captured_at=captured_at,
        )

        text_result: dict[str, Any] | None = None
        if final_transcript_text:
            text_payload = working_payload.model_copy(
                update={"transcript_text": final_transcript_text}
            )
            text_raw_result = _extract_result_or_raise(
                infer_text_emotion(
                    TextEmotionInferRequest(
                        text=final_transcript_text,
                        session_id=session.id,
                        frame_id=payload.frame_id,
                        timestamp=_isoformat(captured_at),
                    )
                )
            )
            text_result = _normalize_text_result(text_raw_result, text_payload)
            _record_inference_result(
                db_session,
                session_id=session.id,
                consultation_turn_id=payload.consultation_turn_id,
                modality="text",
                source_kind="transcript_text",
                source_ref_id=payload.frame_id,
                inference_payload=text_result,
                captured_at=captured_at,
            )

        _refresh_live_payload(session, *(result for result in [speech_result, text_result] if result is not None))
        db_session.add(session)
        db_session.flush()
        bundle_payload = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        db_session.refresh(session)
        return {
            "multimodal_session": _snapshot(session),
            "transcript_text": final_transcript_text,
            "transcript_confidence": asr_payload.get("transcript_confidence"),
            "asr_provider": "dolphin" if final_transcript_text else None,
            "normalized_wav_uri": resolved_normalized_wav_uri,
            "speech_emotion": speech_result,
            "text_emotion": text_result,
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

        capture_row = _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="face",
            capture_kind="frame",
            source_ref_id=str(payload.frame_index),
            capture_payload={
                "consultation_session_id": payload.consultation_session_id,
                "question_key": payload.question_key,
                "mime_type": payload.mime_type,
                "image_format": payload.image_format,
                "image_base64_length": len(payload.image_base64),
                "capture_started_at": _isoformat(payload.capture_started_at),
                "capture_ended_at": _isoformat(payload.capture_ended_at),
                "frame_index": payload.frame_index,
            },
            captured_at=payload.capture_ended_at,
        )

        raw_result = _extract_result_or_raise(
            infer_face_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.image_base64,
                    image_format=payload.image_format,
                    session_id=session.id,
                    frame_id=payload.frame_id or f"face-{payload.frame_index}",
                    timestamp=_isoformat(payload.capture_ended_at),
                )
            )
        )
        face_result = _normalize_face_result(raw_result, payload)
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="face",
            source_kind="frame",
            source_ref_id=str(payload.frame_index),
            inference_payload=face_result,
            captured_at=payload.capture_ended_at,
        )

        _refresh_live_payload(session, face_result)
        db_session.add(session)
        turn_bundle = None
        if payload.consultation_turn_id:
            db_session.flush()
            turn_bundle = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        return {
            "capture_id": capture_row.id,
            "session_id": session.id,
            "question_key": payload.question_key,
            "modality": "face",
            "processing_status": face_result["processing_status"],
            "primary_label": face_result["primary_label"],
            "primary_score": face_result["primary_score"],
            "top_3_labels": face_result["top_3_labels"],
            "quality_flags": face_result["quality_flags"],
            "capture_started_at": face_result["capture_started_at"],
            "capture_ended_at": face_result["capture_ended_at"],
            "created_at": _isoformat(capture_row.created_at),
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

        capture_row = _record_capture(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="pose",
            capture_kind="frame",
            source_ref_id=str(payload.frame_index),
            capture_payload={
                "consultation_session_id": payload.consultation_session_id,
                "question_key": payload.question_key,
                "mime_type": payload.mime_type,
                "image_format": payload.image_format,
                "image_base64_length": len(payload.image_base64),
                "capture_started_at": _isoformat(payload.capture_started_at),
                "capture_ended_at": _isoformat(payload.capture_ended_at),
                "frame_index": payload.frame_index,
            },
            captured_at=payload.capture_ended_at,
        )

        raw_result = _extract_result_or_raise(
            infer_pose_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.image_base64,
                    image_format=payload.image_format,
                    session_id=session.id,
                    frame_id=payload.frame_id or f"pose-{payload.frame_index}",
                    timestamp=_isoformat(payload.capture_ended_at),
                )
            )
        )
        pose_result = _normalize_pose_result(raw_result, payload)
        _record_inference_result(
            db_session,
            session_id=session.id,
            consultation_turn_id=payload.consultation_turn_id,
            modality="pose",
            source_kind="frame",
            source_ref_id=str(payload.frame_index),
            inference_payload=pose_result,
            captured_at=payload.capture_ended_at,
        )

        _refresh_live_payload(session, pose_result)
        db_session.add(session)
        turn_bundle = None
        if payload.consultation_turn_id:
            db_session.flush()
            turn_bundle = _upsert_turn_bundle(db_session, session.id, payload.consultation_turn_id)
        db_session.flush()
        return {
            "capture_id": capture_row.id,
            "session_id": session.id,
            "question_key": payload.question_key,
            "modality": "pose",
            "processing_status": pose_result["processing_status"],
            "primary_label": pose_result["primary_label"],
            "primary_score": pose_result["primary_score"],
            "top_3_labels": pose_result["top_3_labels"],
            "quality_flags": pose_result["quality_flags"],
            "capture_started_at": pose_result["capture_started_at"],
            "capture_ended_at": pose_result["capture_ended_at"],
            "created_at": _isoformat(capture_row.created_at),
            "turn_bundle": turn_bundle,
        }


def get_multimodal_live(session_id: str, acting_user_id: str | None = None) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        live_payload = dict(session.latest_live_payload or {})
        return {
            "session_id": session.id,
            "updated_at": _isoformat(session.updated_at),
            "speech": live_payload.get("speech", _build_pending_live_modality("speech")),
            "text": live_payload.get("text", _build_pending_live_modality("text")),
            "face": live_payload.get("face", _build_pending_live_modality("face")),
            "pose": live_payload.get("pose", _build_pending_live_modality("pose")),
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
