from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any, Iterable, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import get_db_session
from app.models import (
    MultimodalCapture,
    MultimodalInferenceResult,
    MultimodalSession,
    MultimodalTurnBundle,
    MultimodalVisualFrame,
)
from app.schemas import (
    AudioEmotionInferRequest,
    CreateMultimodalSessionRequest,
    FinishEegTurnRequest,
    FrameEmotionInferRequest,
    StartEegTurnRequest,
    SubmitAudioTurnRequest,
    SubmitFrameCaptureRequest,
    TextEmotionInferRequest,
    WarmupMultimodalSessionRequest,
)
from app.services.asr_runtime import DolphinAsrError, get_asr_runtime
from app.services.eeg_runtime import eeg_runtime_service
from app.services.non_eeg_inference import (
    infer_audio_emotion,
    infer_audio_emotion_from_wav_path,
    infer_face_emotion,
    infer_pose_emotion,
    infer_text_emotion,
)
from app.services.non_eeg_runtime import runtime_store
from app.services.audio_processing import (
    AudioProcessingError,
    cleanup_processing_directory,
    convert_to_wav,
    ensure_processing_directory,
    write_source_audio_file,
)
from app.services.multimodal_live_stream import publish_multimodal_live_snapshot
from app.services.multimodal_session_registry import (
    create_or_reuse_session_record,
)
from app.services.multimodal_session_scope import (
    session_allows_flow_run,
)
from app.services.object_storage import download_object_bytes, parse_s3_uri, upload_object_to_bucket
from app.services.visual_key_frame_selector import (
    VisualKeyFrameSelectorInput,
    select_visual_key_frames,
)
from app.services.visual_turn_state_store import (
    finalize_visual_turn_hot_state,
    mark_visual_turn_coarse_checkpoint,
    recover_visual_turn_hot_state_from_bundle,
    read_visual_live_payload,
    read_visual_turn_candidate_payloads,
    read_visual_turn_aggregate_payload,
    read_visual_turn_frame_payloads,
    read_visual_turn_state_payload,
    write_visual_frame_state,
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
_VISUAL_STORAGE_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="multimodal-visual-storage",
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _elapsed_ms(start: float, end: float | None = None) -> int:
    completed = time.perf_counter() if end is None else end
    return max(0, int(round((completed - start) * 1000)))


def _merge_live_payload(
    live_payload: dict[str, Any] | None,
    *results: dict[str, Any],
) -> dict[str, Any]:
    merged_live_payload = dict(live_payload or {})
    for result in results:
        modality = str(result.get("modality") or "").strip().lower()
        if not modality:
            continue
        if modality in {"face", "pose"}:
            merged_live_payload[modality] = {
                "status": result.get("status", "pending"),
                "processing_status": result.get("processing_status", "pending"),
                "primary_label": result.get("primary_label"),
                "primary_score": result.get("primary_score"),
                "top_3_labels": _copy_labels(result.get("top_3_labels")),
                "quality_flags": dict(result.get("quality_flags") or {}),
                "latest_capture_at": result.get("sample_ended_at"),
                "sample_count": result.get("sample_count"),
                "valid_sample_count": result.get("valid_sample_count"),
                "error_message": result.get("error_message"),
            }
        else:
            merged_live_payload[modality] = {
                "status": result.get("status", "pending"),
                "primary_label": result.get("primary_label"),
                "primary_score": result.get("primary_score"),
                "top_3_labels": _copy_labels(result.get("top_3_labels")),
            }
            if modality == "speech":
                merged_live_payload[modality]["audio_uri"] = result.get("audio_uri")
                merged_live_payload[modality]["captured_at"] = result.get("captured_at")
            if modality == "text":
                merged_live_payload[modality]["negative_terms"] = list(result.get("negative_terms") or [])
                merged_live_payload[modality]["transcript_text"] = result.get("transcript_text")
                merged_live_payload[modality]["captured_at"] = result.get("captured_at")
    return merged_live_payload


def _overlay_visual_live_payload(
    base_live_payload: dict[str, Any] | None,
    visual_live_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    merged_payload = dict(base_live_payload or {})
    visual_payload = dict(visual_live_payload or {})
    for modality in ("face", "pose"):
        modality_payload = visual_payload.get(modality)
        if isinstance(modality_payload, dict):
            merged_payload[modality] = dict(modality_payload)
    return merged_payload


def _build_multimodal_live_response(
    session: MultimodalSession,
    *,
    redis_live_payload: dict[str, Any] | None = None,
    eeg_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    live_payload = _overlay_visual_live_payload(
        dict(session.live_state_payload or {}),
        redis_live_payload,
    )
    resolved_eeg_payload = eeg_payload or eeg_runtime_service.get_session_live_payload(session.id)
    eeg_live = dict(resolved_eeg_payload.get("eeg_live") or _build_pending_eeg_live())
    eeg_waves = dict(resolved_eeg_payload.get("eeg_waves") or _build_pending_eeg_waves())
    updated_at = (
        (redis_live_payload or {}).get("updated_at")
        or eeg_live.get("updated_at")
        or _isoformat(session.updated_at)
    )
    return {
        "session_id": session.id,
        "updated_at": updated_at,
        "speech": live_payload.get("speech", _build_pending_live_modality("speech")),
        "text": live_payload.get("text", _build_pending_live_modality("text")),
        "face": live_payload.get("face", _build_pending_live_modality("face")),
        "pose": live_payload.get("pose", _build_pending_live_modality("pose")),
        "eeg_live": eeg_live,
        "eeg_waves": eeg_waves,
    }


def _publish_multimodal_live_snapshot(
    session: MultimodalSession,
    *,
    redis_live_payload: dict[str, Any] | None = None,
    eeg_payload: dict[str, Any] | None = None,
) -> None:
    publish_multimodal_live_snapshot(
        session.id,
        _build_multimodal_live_response(
            session,
            redis_live_payload=redis_live_payload,
            eeg_payload=eeg_payload,
        ),
    )


def _publish_eeg_live_snapshot(
    session_id: str,
    eeg_payload: dict[str, Any],
    wave_delta: dict[str, Any] | None,
) -> None:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            return
        if wave_delta is not None:
            publish_multimodal_live_snapshot(
                session.id,
                {
                    "session_id": session.id,
                    "updated_at": (eeg_payload.get("eeg_live") or {}).get("updated_at"),
                    "eeg_live": dict(eeg_payload.get("eeg_live") or _build_pending_eeg_live()),
                    "eeg_waves": dict(wave_delta),
                },
            )
            return
        _publish_multimodal_live_snapshot(
            session,
            redis_live_payload=read_visual_live_payload(session.id),
            eeg_payload=eeg_payload,
        )


eeg_runtime_service.set_live_update_callback(_publish_eeg_live_snapshot)


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
        "processing_status": "pending",
        "primary_label": None,
        "primary_score": None,
    }
    if modality in {"speech", "text"}:
        base["top_3_labels"] = []
    if modality == "text":
        base["negative_terms"] = []
        base["transcript_text"] = None
        base["captured_at"] = None
    if modality == "speech":
        base["audio_uri"] = None
        base["captured_at"] = None
    if modality in {"face", "pose"}:
        base["latest_capture_at"] = None
        base["top_3_labels"] = []
        base["quality_flags"] = {}
        base["sample_count"] = 0
        base["valid_sample_count"] = 0
        base["error_message"] = None
    return base


def _build_pending_eeg_live() -> dict[str, Any]:
    return {
        "status": "pending",
        "device_status": "pending",
        "device_id": None,
        "channel_names": list(get_settings()["eeg_channel_names"]),
        "sampling_rate": int(get_settings()["eeg_sampling_rate"]),
        "updated_at": None,
        "turn_id": None,
        "model_name": "eeg_3class",
        "model_version": None,
        "latest_result": None,
        "latest_results": [],
        "error_message": None,
    }


def _build_pending_eeg_waves() -> dict[str, Any]:
    return {
        "status": "pending",
        "channel_names": list(get_settings()["eeg_channel_names"]),
        "sampling_rate": int(get_settings()["eeg_sampling_rate"]),
        "samples": [],
    }


def _bool_ratio(payloads: Sequence[dict[str, Any]], key: str) -> float:
    if not payloads:
        return 0.0
    positive = 0
    for payload in payloads:
        quality_flags = payload.get("quality_flags") or {}
        if bool(quality_flags.get(key)):
            positive += 1
    return round(positive / len(payloads), 4)


def _resolve_frame_quality_keys(modality: str) -> tuple[str, ...]:
    if modality == "face":
        return ("no_face", "blur", "low_light")
    return ("no_pose", "body_cutoff", "motion_blur")


def _extract_distribution_label(payload: dict[str, Any], modality: str) -> str | None:
    quality_flags = payload.get("quality_flags") or {}
    if modality == "face" and bool(quality_flags.get("no_face")):
        return None
    if modality == "pose" and bool(quality_flags.get("no_pose")):
        return None

    primary_label = str(payload.get("primary_label") or "").strip()
    if primary_label:
        return primary_label

    top_label = _copy_labels(payload.get("top_3_labels"), limit=1)
    if top_label:
        return str(top_label[0]["label"]).strip() or None
    return None


def _build_label_distribution(
    payloads: Sequence[dict[str, Any]],
    modality: str,
) -> tuple[list[dict[str, Any]], str | None, float | None, int]:
    counts: Counter[str] = Counter()
    for payload in payloads:
        label = _extract_distribution_label(payload, modality)
        if label:
            counts[label] += 1

    valid_sample_count = sum(counts.values())
    if valid_sample_count <= 0:
        return [], None, None, 0

    sorted_items = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    )
    distribution = [
        {
            "label": label,
            "count": count,
            "ratio": round(count / valid_sample_count, 4),
        }
        for label, count in sorted_items
    ]
    primary_label = distribution[0]["label"]
    primary_ratio = distribution[0]["ratio"]
    return distribution, primary_label, primary_ratio, valid_sample_count


def _build_quality_distribution(
    payloads: Sequence[dict[str, Any]],
    modality: str,
) -> dict[str, dict[str, Any]]:
    distribution: dict[str, dict[str, Any]] = {}
    for key in _resolve_frame_quality_keys(modality):
        positive_count = 0
        for payload in payloads:
            quality_flags = payload.get("quality_flags") or {}
            if bool(quality_flags.get(key)):
                positive_count += 1
        ratio = round(positive_count / len(payloads), 4) if payloads else 0.0
        distribution[key] = {
            "count": positive_count,
            "ratio": ratio,
        }
    return distribution


def _summarize_frame_payloads(
    modality: str,
    payloads: Sequence[dict[str, Any]],
    *,
    summary_type: str,
) -> dict[str, Any]:
    if not payloads:
        return {
            "summary_type": summary_type,
            "primary_label": None,
            "primary_score": None,
            "primary_ratio": None,
            "sample_count": 0,
            "valid_sample_count": 0,
            "label_distribution": [],
            "quality_distribution": _build_quality_distribution([], modality),
            "quality_flags": {
                f"{key}_ratio": 0.0 for key in _resolve_frame_quality_keys(modality)
            },
        }

    (
        label_distribution,
        primary_label,
        primary_ratio,
        valid_sample_count,
    ) = _build_label_distribution(payloads, modality)
    quality_distribution = _build_quality_distribution(payloads, modality)
    return {
        "summary_type": summary_type,
        "primary_label": primary_label,
        "primary_score": primary_ratio,
        "primary_ratio": primary_ratio,
        "sample_count": len(payloads),
        "valid_sample_count": valid_sample_count,
        "label_distribution": label_distribution,
        "quality_distribution": quality_distribution,
        "quality_flags": {
            f"{key}_ratio": quality_distribution[key]["ratio"]
            for key in quality_distribution
        },
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
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
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
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
        "primary_label": raw_result.get("label"),
        "primary_score": float(raw_result.get("score") or 0.0),
        "top_3_labels": top_3_labels,
        "negative_terms": _extract_negative_terms(transcript_text),
        "transcript_text": transcript_text,
        "captured_at": _isoformat(payload.captured_at),
    }


def _normalize_face_result(raw_result: dict[str, Any], payload: SubmitFrameCaptureRequest) -> dict[str, Any]:
    status = str(raw_result.get("status") or "error").lower()
    processing_status = "completed" if status in {"ok", "no_face"} else "failed"
    scores = raw_result.get("scores") or {}
    quality_flags = dict(raw_result.get("quality_flags") or {})
    return {
        "modality": "face",
        "status": "ready" if processing_status == "completed" else "failed",
        "processing_status": processing_status,
        "question_key": payload.question_key,
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
        "primary_label": raw_result.get("dominant_emotion_zh"),
        "primary_score": float(raw_result.get("confidence") or 0.0),
        "top_3_labels": _top_labels_from_scores(scores, limit=3),
        "quality_flags": {
            "no_face": status == "no_face",
            "blur": bool(quality_flags.get("blur", False)),
            "low_light": bool(quality_flags.get("low_light", False)),
        },
        "sample_started_at": _isoformat(payload.sample_started_at),
        "sample_ended_at": _isoformat(payload.sample_ended_at),
        "sample_index": payload.sample_index,
        "error_message": None if processing_status == "completed" else str(raw_result.get("status") or "face_inference_failed"),
    }


def _build_failed_face_result(
    payload: SubmitFrameCaptureRequest,
    *,
    error_message: str,
) -> dict[str, Any]:
    return {
        "modality": "face",
        "status": "failed",
        "processing_status": "failed",
        "question_key": payload.question_key,
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
        "primary_label": None,
        "primary_score": None,
        "top_3_labels": [],
        "quality_flags": {
            "no_face": False,
            "blur": False,
            "low_light": False,
        },
        "sample_started_at": _isoformat(payload.sample_started_at),
        "sample_ended_at": _isoformat(payload.sample_ended_at),
        "sample_index": payload.sample_index,
        "error_message": error_message,
    }


def _compute_face_quality_flags(image_bytes: bytes) -> dict[str, bool]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if frame is None:
            return {"blur": False, "low_light": False}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        return {
            "blur": blur_score < 45.0,
            "low_light": brightness < 55.0,
        }
    except Exception:
        return {"blur": False, "low_light": False}


def _build_frame_storage_uri(
    *,
    modality: str,
    session_id: str,
    turn_id: str | None,
    sample_index: int | None,
    image_format: str,
    image_bytes: bytes,
) -> str | None:
    bucket_name = str(get_settings()["multimodal_bucket"])
    normalized_format = (image_format or "jpg").strip().lower() or "jpg"
    extension = "jpg" if normalized_format == "jpeg" else normalized_format
    if extension not in {"jpg", "png", "bmp"}:
        extension = "jpg"
    object_key = "/".join(
        [
            "captures",
            modality,
            session_id,
            turn_id or "unbound",
            f"sample-{sample_index or 0}.{extension}",
        ]
    )
    try:
        return upload_object_to_bucket(
            bucket_name=bucket_name,
            object_key=object_key,
            file_bytes=image_bytes,
            content_type=f"image/{extension}",
        )
    except Exception:
        return None


def _build_visual_frame_storage_uri(
    *,
    session_id: str,
    turn_id: str | None,
    sample_index: int | None,
    image_format: str,
    image_bytes: bytes,
) -> str | None:
    return _build_frame_storage_uri(
        modality="visual",
        session_id=session_id,
        turn_id=turn_id,
        sample_index=sample_index,
        image_format=image_format,
        image_bytes=image_bytes,
    )


def _record_visual_frame(
    db_session,
    *,
    session_id: str,
    turn_id: str | None,
    flow_run_id: str | None,
    stage_id: str | None,
    question_key: str | None,
    sample_index: int | None,
    sample_started_at: datetime | None,
    sample_ended_at: datetime | None,
    mime_type: str | None,
    capture_payload: dict[str, Any],
    captured_at: datetime | None,
    storage_uri: str | None,
    origin_flow_type: str | None = None,
) -> MultimodalVisualFrame:
    row = MultimodalVisualFrame(
        session_id=session_id,
        turn_id=turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        sample_index=sample_index,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
        mime_type=mime_type,
        storage_uri=storage_uri,
        capture_payload=capture_payload,
        captured_at=captured_at,
        created_at=_utcnow(),
    )
    db_session.add(row)
    db_session.flush()
    return row


def _build_frame_capture_payload(payload: SubmitFrameCaptureRequest) -> dict[str, Any]:
    return {
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "question_key": payload.question_key,
        "mime_type": payload.mime_type,
        "image_format": payload.image_format,
        "image_bytes_length": payload.image_bytes_length(),
        "sample_started_at": _isoformat(payload.sample_started_at),
        "sample_ended_at": _isoformat(payload.sample_ended_at),
        "sample_index": payload.sample_index,
    }


def _build_frame_capture_response(
    *,
    capture_row: MultimodalCapture,
    session_id: str,
    question_key: str,
    modality: str,
    result_payload: dict[str, Any],
    storage_uri: str | None,
    turn_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "capture_id": capture_row.id,
        "session_id": session_id,
        "question_key": question_key,
        "modality": modality,
        "processing_status": result_payload["processing_status"],
        "primary_label": result_payload["primary_label"],
        "primary_score": result_payload["primary_score"],
        "top_3_labels": result_payload["top_3_labels"],
        "quality_flags": result_payload["quality_flags"],
        "sample_started_at": result_payload["sample_started_at"],
        "sample_ended_at": result_payload["sample_ended_at"],
        "sample_count": result_payload.get("sample_count"),
        "valid_sample_count": result_payload.get("valid_sample_count"),
        "storage_uri": storage_uri,
        "error_message": result_payload.get("error_message"),
        "created_at": _isoformat(capture_row.created_at),
        "turn_bundle": turn_bundle,
    }


def _build_visual_frame_response(
    *,
    visual_frame: MultimodalVisualFrame,
    session_id: str,
    turn_id: str | None,
    question_key: str,
    sample_index: int,
    sample_started_at: datetime,
    sample_ended_at: datetime,
    storage_uri: str | None,
) -> dict[str, Any]:
    return {
        "visual_frame_id": visual_frame.id,
        "session_id": session_id,
        "turn_id": turn_id,
        "question_key": question_key,
        "sample_index": sample_index,
        "sample_started_at": _isoformat(sample_started_at),
        "sample_ended_at": _isoformat(sample_ended_at),
        "storage_uri": storage_uri,
        "created_at": _isoformat(visual_frame.created_at),
    }


def _build_visual_pipeline_status(
    *,
    state_store: str,
    live_state_source: str,
    turn_bundle_source: str,
    degraded: bool,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "state_store": state_store,
        "live_state_source": live_state_source,
        "turn_bundle_source": turn_bundle_source,
        "degraded": degraded,
        "fallback_reason": fallback_reason,
    }


def _build_visual_capture_response(
    *,
    visual_frame: MultimodalVisualFrame,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
    storage_uri: str | None,
    face_response: dict[str, Any],
    pose_response: dict[str, Any],
    turn_bundle: dict[str, Any] | None,
    visual_pipeline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "visual_frame": _build_visual_frame_response(
            visual_frame=visual_frame,
            session_id=session.id,
            turn_id=payload.turn_id,
            question_key=payload.question_key,
            sample_index=payload.sample_index,
            sample_started_at=payload.sample_started_at,
            sample_ended_at=payload.sample_ended_at,
            storage_uri=storage_uri,
        ),
        "face_result": face_response,
        "pose_result": pose_response,
        "turn_bundle": turn_bundle,
        "visual_pipeline": visual_pipeline,
        "multimodal_session": _snapshot(session),
    }


def _load_latest_inference_payload_by_sample_id(
    db_session,
    *,
    sample_id: str,
    modality: str,
) -> dict[str, Any] | None:
    row = db_session.execute(
        select(MultimodalInferenceResult).where(
            MultimodalInferenceResult.sample_id == sample_id,
            MultimodalInferenceResult.modality == modality,
        ).order_by(MultimodalInferenceResult.created_at.desc())
    ).scalars().first()
    if row is None:
        return None
    return dict(row.inference_payload or {})


def _find_existing_visual_capture_response(
    db_session,
    *,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
) -> dict[str, Any] | None:
    if not hasattr(db_session, "execute"):
        return None
    visual_frame = db_session.execute(
        select(MultimodalVisualFrame).where(
            MultimodalVisualFrame.session_id == session.id,
            MultimodalVisualFrame.turn_id == payload.turn_id,
            MultimodalVisualFrame.question_key == payload.question_key,
            MultimodalVisualFrame.sample_index == payload.sample_index,
        ).order_by(MultimodalVisualFrame.created_at.desc())
    ).scalars().first()
    if visual_frame is None:
        return None

    face_capture = db_session.execute(
        select(MultimodalCapture).where(
            MultimodalCapture.session_id == session.id,
            MultimodalCapture.turn_id == payload.turn_id,
            MultimodalCapture.question_key == payload.question_key,
            MultimodalCapture.sample_index == payload.sample_index,
            MultimodalCapture.modality == "face",
            MultimodalCapture.source_ref_id == visual_frame.id,
        ).order_by(MultimodalCapture.created_at.desc())
    ).scalars().first()
    pose_capture = db_session.execute(
        select(MultimodalCapture).where(
            MultimodalCapture.session_id == session.id,
            MultimodalCapture.turn_id == payload.turn_id,
            MultimodalCapture.question_key == payload.question_key,
            MultimodalCapture.sample_index == payload.sample_index,
            MultimodalCapture.modality == "pose",
            MultimodalCapture.source_ref_id == visual_frame.id,
        ).order_by(MultimodalCapture.created_at.desc())
    ).scalars().first()
    if face_capture is None or pose_capture is None:
        return None

    face_result = _load_latest_inference_payload_by_sample_id(
        db_session,
        sample_id=face_capture.id,
        modality="face",
    )
    pose_result = _load_latest_inference_payload_by_sample_id(
        db_session,
        sample_id=pose_capture.id,
        modality="pose",
    )
    if face_result is None or pose_result is None:
        return None

    turn_bundle = None
    if payload.turn_id:
        bundle_row = db_session.execute(
            select(MultimodalTurnBundle).where(
                MultimodalTurnBundle.session_id == session.id,
                MultimodalTurnBundle.turn_id == payload.turn_id,
            )
        ).scalar_one_or_none()
        if bundle_row is not None:
            turn_bundle = dict(bundle_row.bundle_payload or {})

    _apply_frame_summary_counts(
        face_result,
        modality="face",
        turn_bundle=turn_bundle,
        sample_index=payload.sample_index,
    )
    _apply_frame_summary_counts(
        pose_result,
        modality="pose",
        turn_bundle=turn_bundle,
        sample_index=payload.sample_index,
    )
    return _build_visual_capture_response(
        visual_frame=visual_frame,
        session=session,
        payload=payload,
        storage_uri=visual_frame.storage_uri,
        face_response=_build_frame_capture_response(
            capture_row=face_capture,
            session_id=session.id,
            question_key=payload.question_key,
            modality="face",
            result_payload=face_result,
            storage_uri=face_capture.storage_uri,
            turn_bundle=turn_bundle,
        ),
        pose_response=_build_frame_capture_response(
            capture_row=pose_capture,
            session_id=session.id,
            question_key=payload.question_key,
            modality="pose",
            result_payload=pose_result,
            storage_uri=pose_capture.storage_uri,
            turn_bundle=turn_bundle,
        ),
        turn_bundle=turn_bundle,
        visual_pipeline=_build_visual_pipeline_status(
            state_store="persisted_only",
            live_state_source="snapshot",
            turn_bundle_source="database" if turn_bundle else "snapshot",
            degraded=False,
        ),
    )


def _build_current_turn_bundle_from_redis(
    db_session,
    *,
    session_id: str,
    turn_id: str | None,
    flow_run_id: str,
    stage_id: str | None,
    question_key: str,
    redis_turn_aggregate: dict[str, Any] | None,
    origin_flow_type: str | None = None,
) -> dict[str, Any] | None:
    if not turn_id or redis_turn_aggregate is None:
        return None
    return _build_turn_bundle_payload(
        db_session,
        session_id,
        turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        face_summary=(redis_turn_aggregate or {}).get("face_features"),
        pose_summary=(redis_turn_aggregate or {}).get("pose_features"),
    )


def _apply_visual_coarse_checkpoint(
    db_session,
    *,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
    face_result: dict[str, Any],
    pose_result: dict[str, Any],
    redis_turn_aggregate: dict[str, Any] | None,
    redis_turn_state: dict[str, Any] | None,
) -> bool:
    if redis_turn_aggregate is None:
        return False

    checkpoint_at = _utcnow()
    retained_frame_payloads = read_visual_turn_frame_payloads(
        session.id,
        payload.turn_id,
        sample_indexes=(redis_turn_state or {}).get("all_frame_sample_indexes"),
    )
    retained_candidate_payloads = read_visual_turn_candidate_payloads(
        session.id,
        payload.turn_id,
        sample_indexes=(redis_turn_state or {}).get("candidate_sample_indexes"),
    )
    checkpoint_selection = select_visual_key_frames(
        VisualKeyFrameSelectorInput(
            frame_payloads=retained_frame_payloads,
            candidate_payloads=retained_candidate_payloads,
            turn_state_payload=redis_turn_state,
            turn_aggregate_payload=redis_turn_aggregate,
        )
    ).to_payload()
    checkpoint_key_frame_indexes = sorted(
        {
            int(value)
            for value in list((redis_turn_state or {}).get("checkpoint_key_frame_sample_indexes") or [])
            + [
                int(item.get("sample_index") or 0)
                for item in list(checkpoint_selection.get("selected_frames") or [])
            ]
            if int(value) > 0
        }
    )
    retained_candidate_indexes = sorted(
        {
            int(value)
            for value in list((redis_turn_state or {}).get("candidate_sample_indexes") or [])
            if int(value) > 0
        }
    )
    retained_frame_indexes = sorted(
        {
            int(value)
            for value in list((redis_turn_state or {}).get("recent_frame_sample_indexes") or [])
            + checkpoint_key_frame_indexes
            + retained_candidate_indexes
            if int(value) > 0
        }
    )

    _refresh_live_payload(session, face_result, pose_result)
    db_session.add(session)
    if payload.turn_id:
        _upsert_turn_bundle(
            db_session,
            session.id,
            payload.turn_id,
            flow_run_id=payload.flow_run_id,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
            face_summary=(redis_turn_aggregate or {}).get("face_features"),
            pose_summary=(redis_turn_aggregate or {}).get("pose_features"),
            visual_key_frames=[],
            visual_selection={
                "checkpoint": True,
                "checkpoint_at": _isoformat(checkpoint_at),
                "frame_count": int((redis_turn_state or {}).get("frame_count") or 0),
                "retained_frame_count": len(retained_frame_indexes),
                "checkpoint_key_frame_count": len(checkpoint_key_frame_indexes),
                "candidate_count": len(
                    list((redis_turn_state or {}).get("candidate_sample_indexes") or [])
                ),
                "source": "coarse_checkpoint",
            },
        )
    db_session.flush()
    if payload.turn_id:
        mark_visual_turn_coarse_checkpoint(
            session.id,
            payload.turn_id,
            checkpointed_at=checkpoint_at,
            checkpoint_frame_count=int((redis_turn_state or {}).get("frame_count") or 0),
            retained_frame_sample_indexes=retained_frame_indexes,
            checkpoint_key_frame_sample_indexes=checkpoint_key_frame_indexes,
            retained_candidate_sample_indexes=retained_candidate_indexes,
        )
    logger.info(
        "visual turn coarse checkpoint applied session_id=%s turn_id=%s sample_index=%s frame_count=%s retained_frames=%s checkpoint_key_frames=%s",
        session.id,
        payload.turn_id,
        payload.sample_index,
        (redis_turn_state or {}).get("frame_count"),
        len(retained_frame_indexes),
        len(checkpoint_key_frame_indexes),
    )
    return True


def _build_hot_path_visual_capture_response(
    *,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
    storage_uri: str | None,
    face_result: dict[str, Any],
    pose_result: dict[str, Any],
    turn_bundle: dict[str, Any] | None,
    visual_pipeline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    visual_frame_ref = SimpleNamespace(
        id=f"redis-vf-{session.id}-{payload.turn_id or 'unbound'}-{payload.sample_index}",
        created_at=payload.sample_ended_at,
    )
    face_capture_ref = SimpleNamespace(
        id=f"redis-face-{session.id}-{payload.turn_id or 'unbound'}-{payload.sample_index}",
        created_at=payload.sample_ended_at,
    )
    pose_capture_ref = SimpleNamespace(
        id=f"redis-pose-{session.id}-{payload.turn_id or 'unbound'}-{payload.sample_index}",
        created_at=payload.sample_ended_at,
    )
    session_snapshot = _snapshot(session)
    session_snapshot["status"] = "active" if session_snapshot.get("status") == "created" else session_snapshot.get("status")
    session_snapshot["updated_at"] = payload.sample_ended_at
    session_snapshot["live_state_payload"] = _merge_live_payload(
        dict(session.live_state_payload or {}),
        face_result,
        pose_result,
    )
    return {
        "visual_frame": _build_visual_frame_response(
            visual_frame=visual_frame_ref,  # type: ignore[arg-type]
            session_id=session.id,
            turn_id=payload.turn_id,
            question_key=payload.question_key,
            sample_index=payload.sample_index,
            sample_started_at=payload.sample_started_at,
            sample_ended_at=payload.sample_ended_at,
            storage_uri=storage_uri,
        ),
        "face_result": _build_frame_capture_response(
            capture_row=face_capture_ref,  # type: ignore[arg-type]
            session_id=session.id,
            question_key=payload.question_key,
            modality="face",
            result_payload=face_result,
            storage_uri=storage_uri,
            turn_bundle=turn_bundle,
        ),
        "pose_result": _build_frame_capture_response(
            capture_row=pose_capture_ref,  # type: ignore[arg-type]
            session_id=session.id,
            question_key=payload.question_key,
            modality="pose",
            result_payload=pose_result,
            storage_uri=storage_uri,
            turn_bundle=turn_bundle,
        ),
        "turn_bundle": turn_bundle,
        "visual_pipeline": visual_pipeline,
        "multimodal_session": session_snapshot,
    }


def _log_visual_capture_timing(
    *,
    session_id: str,
    turn_id: str | None,
    sample_index: int,
    image_bytes_length: int,
    face_result: dict[str, Any],
    pose_result: dict[str, Any],
    storage_uri: str | None,
    turn_bundle: dict[str, Any] | None,
    total_ms: int,
    face_infer_ms: int,
    pose_infer_ms: int,
    inference_total_ms: int,
    storage_wait_ms: int,
    redis_write_ms: int,
    redis_write_success: bool,
    persistence_ms: int,
    coarse_checkpoint_due: bool,
    coarse_checkpoint_applied: bool,
) -> None:
    logger.info(
        "visual capture timing session_id=%s turn_id=%s sample_index=%s bytes=%s total_ms=%s "
        "face_infer_ms=%s pose_infer_ms=%s inference_total_ms=%s storage_wait_ms=%s "
        "redis_write_ms=%s redis_write_success=%s persistence_ms=%s coarse_checkpoint_due=%s coarse_checkpoint_applied=%s "
        "upload_overlapped=%s storage_uri_present=%s turn_bundle_present=%s "
        "face_status=%s pose_status=%s",
        session_id,
        turn_id,
        sample_index,
        image_bytes_length,
        total_ms,
        face_infer_ms,
        pose_infer_ms,
        inference_total_ms,
        storage_wait_ms,
        redis_write_ms,
        redis_write_success,
        persistence_ms,
        coarse_checkpoint_due,
        coarse_checkpoint_applied,
        storage_wait_ms < inference_total_ms,
        storage_uri is not None,
        turn_bundle is not None,
        face_result.get("processing_status"),
        pose_result.get("processing_status"),
    )


def _infer_face_capture_result(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
) -> dict[str, Any]:
    try:
        raw_result = _extract_result_or_raise(
            infer_face_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.require_image_base64(),
                    image_format=payload.image_format,
                    session_id=session_id,
                    frame_id=payload.frame_id or f"face-{payload.sample_index}",
                    timestamp=_isoformat(payload.sample_ended_at),
                )
            )
        )
        raw_result["quality_flags"] = {
            **_compute_face_quality_flags(payload.require_image_bytes()),
            **dict(raw_result.get("quality_flags") or {}),
        }
        return _normalize_face_result(raw_result, payload)
    except MultimodalServiceError as exc:
        return _build_failed_face_result(payload, error_message=exc.message)


def _infer_pose_capture_result(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
) -> dict[str, Any]:
    try:
        raw_result = _extract_result_or_raise(
            infer_pose_emotion(
                FrameEmotionInferRequest(
                    image_base64=payload.require_image_base64(),
                    image_format=payload.image_format,
                    session_id=session_id,
                    turn_id=payload.turn_id,
                    frame_id=payload.frame_id or f"pose-{payload.sample_index}",
                    timestamp=_isoformat(payload.sample_ended_at),
                )
            )
        )
        logger.info(
            "pose raw result session_id=%s turn_id=%s sample_index=%s label=%s score=%s frames=%s confidences=%s",
            session_id,
            payload.turn_id,
            payload.sample_index,
            raw_result.get("label"),
            raw_result.get("score"),
            ((raw_result.get("extra") or {}).get("frames")),
            ((raw_result.get("extra") or {}).get("confidences")),
        )
        return _normalize_pose_result(raw_result, payload)
    except MultimodalServiceError as exc:
        return _build_failed_pose_result(payload, error_message=exc.message)


def _record_frame_capture_result(
    db_session,
    *,
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    modality: str,
    source_ref_id: str,
    storage_uri: str | None,
    inference_payload: dict[str, Any],
    sample_id: str | None = None,
) -> MultimodalCapture:
    capture_row = _record_capture(
        db_session,
        session_id=session_id,
        turn_id=payload.turn_id,
        flow_run_id=payload.flow_run_id,
        origin_flow_type=payload.origin_flow_type,
        stage_id=payload.stage_id,
        question_key=payload.question_key,
        modality=modality,
        capture_kind="frame",
        source_ref_id=source_ref_id,
        sample_index=payload.sample_index,
        sample_started_at=payload.sample_started_at,
        sample_ended_at=payload.sample_ended_at,
        capture_payload={
            **_build_frame_capture_payload(payload),
            **({"visual_frame_id": sample_id} if sample_id else {}),
        },
        captured_at=payload.sample_ended_at,
    )
    capture_row.storage_uri = storage_uri
    db_session.add(capture_row)
    _record_inference_result(
        db_session,
        session_id=session_id,
        turn_id=payload.turn_id,
        flow_run_id=payload.flow_run_id,
        origin_flow_type=payload.origin_flow_type,
        stage_id=payload.stage_id,
        question_key=payload.question_key,
        modality=modality,
        source_kind="frame",
        source_ref_id=source_ref_id,
        sample_id=capture_row.id,
        inference_payload=inference_payload,
        captured_at=payload.sample_ended_at,
    )
    return capture_row


def _apply_frame_summary_counts(
    result_payload: dict[str, Any],
    *,
    modality: str,
    turn_bundle: dict[str, Any] | None,
    sample_index: int,
) -> None:
    feature_key = f"{modality}_features"
    features = dict((turn_bundle or {}).get(feature_key) or {})
    if features:
        result_payload["sample_count"] = features.get("sample_count")
        result_payload["valid_sample_count"] = features.get("valid_sample_count")
    if "sample_count" not in result_payload:
        result_payload["sample_count"] = sample_index
    if "valid_sample_count" not in result_payload:
        result_payload["valid_sample_count"] = None


def _submit_face_capture_with_session(
    db_session,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
    *,
    storage_uri: str | None,
    source_ref_id: str,
    sample_id: str | None = None,
) -> dict[str, Any]:
    face_result = _infer_face_capture_result(session.id, payload)
    capture_row = _record_frame_capture_result(
        db_session,
        session_id=session.id,
        payload=payload,
        modality="face",
        source_ref_id=source_ref_id,
        storage_uri=storage_uri,
        inference_payload=face_result,
        sample_id=sample_id,
    )

    turn_bundle = None
    if payload.turn_id:
        turn_bundle = _upsert_turn_bundle(
            db_session,
            session.id,
            payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
        )
    _apply_frame_summary_counts(
        face_result,
        modality="face",
        turn_bundle=turn_bundle,
        sample_index=payload.sample_index,
    )
    _refresh_live_payload(session, face_result)
    db_session.add(session)
    db_session.flush()
    _publish_multimodal_live_snapshot(session)
    return _build_frame_capture_response(
        capture_row=capture_row,
        session_id=session.id,
        question_key=payload.question_key,
        modality="face",
        result_payload=face_result,
        storage_uri=storage_uri,
        turn_bundle=turn_bundle,
    )


def _submit_pose_capture_with_session(
    db_session,
    session: MultimodalSession,
    payload: SubmitFrameCaptureRequest,
    *,
    storage_uri: str | None,
    source_ref_id: str,
    sample_id: str | None = None,
) -> dict[str, Any]:
    pose_result = _infer_pose_capture_result(session.id, payload)
    capture_row = _record_frame_capture_result(
        db_session,
        session_id=session.id,
        payload=payload,
        modality="pose",
        source_ref_id=source_ref_id,
        storage_uri=storage_uri,
        inference_payload=pose_result,
        sample_id=sample_id,
    )

    turn_bundle = None
    if payload.turn_id:
        turn_bundle = _upsert_turn_bundle(
            db_session,
            session.id,
            payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
        )
    _apply_frame_summary_counts(
        pose_result,
        modality="pose",
        turn_bundle=turn_bundle,
        sample_index=payload.sample_index,
    )
    _refresh_live_payload(session, pose_result)
    db_session.add(session)
    db_session.flush()
    _publish_multimodal_live_snapshot(session)
    return _build_frame_capture_response(
        capture_row=capture_row,
        session_id=session.id,
        question_key=payload.question_key,
        modality="pose",
        result_payload=pose_result,
        storage_uri=storage_uri,
        turn_bundle=turn_bundle,
    )


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
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
        "primary_label": None if is_collecting else label,
        "primary_score": None if is_collecting else float(raw_result.get("score") or 0.0),
        "top_3_labels": [] if is_collecting else _top_labels_from_scores(confidences, limit=3),
        "quality_flags": {
            "no_pose": is_no_pose,
            "body_cutoff": False,
            "motion_blur": False,
        },
        "sample_started_at": _isoformat(payload.sample_started_at),
        "sample_ended_at": _isoformat(payload.sample_ended_at),
        "sample_index": payload.sample_index,
        "error_message": None,
    }


def _build_failed_pose_result(
    payload: SubmitFrameCaptureRequest,
    *,
    error_message: str,
) -> dict[str, Any]:
    return {
        "modality": "pose",
        "status": "failed",
        "processing_status": "failed",
        "question_key": payload.question_key,
        "flow_run_id": payload.flow_run_id,
        "origin_flow_type": payload.origin_flow_type,
        "turn_id": payload.turn_id,
        "primary_label": None,
        "primary_score": None,
        "top_3_labels": [],
        "quality_flags": {
            "no_pose": False,
            "body_cutoff": False,
            "motion_blur": False,
        },
        "sample_started_at": _isoformat(payload.sample_started_at),
        "sample_ended_at": _isoformat(payload.sample_ended_at),
        "sample_index": payload.sample_index,
        "error_message": error_message,
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
        f"consultation-audio/{payload.flow_run_id}/"
        f"{payload.turn_id}/normalized/response.wav"
    )
    return bucket_name, object_key


def _prepare_normalized_audio(
    payload: SubmitAudioTurnRequest,
) -> PreparedNormalizedAudio:
    if not payload.original_audio_uri:
        raise MultimodalServiceError("original_audio_uri is required", 4006, 422)
    source_suffix = _resolve_audio_source_suffix(payload)
    processing_id = f"turn-{payload.turn_id}"
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
    turn_id: str,
    audio_base64: str,
    audio_format: str | None,
) -> PreparedNormalizedAudio:
    processing_id = f"turn-asr-{turn_id}"
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
    if not acting_user_id:
        raise MultimodalServiceError("missing acting user id", 4013, 401)
    session_user_id = str(getattr(session, "user_id", None) or "").strip()
    if session_user_id and session_user_id != acting_user_id:
        raise MultimodalServiceError("multimodal session access denied", 4031, 403)


def _normalize_modalities(modalities: list[str]) -> list[str]:
    valid = {"text", "audio", "face", "pose", "eeg"}
    normalized: list[str] = []
    for item in modalities:
        key = str(item).strip().lower()
        if key in valid and key not in normalized:
            normalized.append(key)
    return normalized or ["text", "audio", "face", "pose", "eeg"]


def _stage_context_payload(session: MultimodalSession) -> dict[str, Any]:
    return dict(session.stage_context or {})


def _resolve_origin_flow_type(
    session: MultimodalSession,
    candidate: str | None,
) -> str:
    return (
        str(candidate or "").strip()
        or str(getattr(session, "flow_type", None) or "").strip()
        or "consultation"
    )


def _snapshot(session: MultimodalSession) -> dict[str, Any]:
    started_at = session.started_at or session.created_at
    created_at = session.created_at or started_at
    return {
        "id": session.id,
        "session_id": session.id,
        "user_id": session.user_id,
        "encounter_session_id": session.encounter_session_id,
        "scope_type": session.scope_type,
        "scope_id": session.scope_id,
        "flow_type": session.flow_type,
        "flow_run_id": session.flow_run_id,
        "status": session.status,
        "stage_context": _stage_context_payload(session),
        "enabled_modalities": list(session.enabled_modalities or []),
        "live_state_payload": dict(session.live_state_payload or {}),
        "notes": session.notes,
        "started_at": started_at.isoformat() if started_at else None,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": session.updated_at.isoformat(),
        "warmed_up_at": (
            session.warmed_up_at.isoformat() if session.warmed_up_at else None
        ),
        "completed_at": (
            session.completed_at.isoformat() if session.completed_at else None
        ),
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
    stage_context = payload.stage_context.model_dump() if payload.stage_context else {}
    with get_db_session() as db_session:
        session = create_or_reuse_session_record(
            db_session,
            payload=payload,
            effective_user_id=effective_user_id,
            stage_context=stage_context,
            enabled_modalities=_normalize_modalities(payload.enabled_modalities),
            now_factory=_utcnow,
            create_status="created",
            status_on_update=None,
            fallback_flow_run_id_factory=lambda session_id: session_id,
            acting_user_id=acting_user_id,
            access_validator=_ensure_session_access,
        )
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
            runtime_store.get_pose_engine()
        if "eeg" in modalities:
            eeg_runtime_service.warmup()

        now = _utcnow()
        session.status = "warm"
        session.warmed_up_at = now
        session.updated_at = now
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)
        return _snapshot(session)


def start_eeg_turn(
    session_id: str,
    payload: StartEegTurnRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        result = eeg_runtime_service.begin_turn(
            session_id=session.id,
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id or session.flow_run_id,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
        )
        session.updated_at = _utcnow()
        db_session.add(session)
        db_session.flush()
        _publish_multimodal_live_snapshot(
            session,
            redis_live_payload=read_visual_live_payload(session.id),
        )
        return result


def finish_eeg_turn(
    session_id: str,
    turn_id: str,
    payload: FinishEegTurnRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        result = eeg_runtime_service.finish_turn(
            session_id=session.id,
            turn_id=turn_id,
            reason=str(payload.reason or "completed"),
        )
        session.updated_at = _utcnow()
        db_session.add(session)
        db_session.flush()
        _publish_multimodal_live_snapshot(
            session,
            redis_live_payload=read_visual_live_payload(session.id),
        )
        return result


def get_eeg_turn_results(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        return {
            "session_id": session.id,
            "turn_id": turn_id,
            "modality": "eeg",
            "results": _load_inference_payloads(
                db_session,
                session_id=session.id,
                modality="eeg",
                turn_id=turn_id,
            ),
        }


def _record_capture(
    db_session,
    *,
    session_id: str,
    turn_id: str | None,
    flow_run_id: str | None,
    stage_id: str | None,
    question_key: str | None,
    modality: str,
    capture_kind: str,
    source_ref_id: str | None,
    sample_index: int | None,
    sample_started_at: datetime | None,
    sample_ended_at: datetime | None,
    capture_payload: dict[str, Any],
    captured_at: datetime | None,
    origin_flow_type: str | None = None,
) -> MultimodalCapture:
    row = MultimodalCapture(
        session_id=session_id,
        turn_id=turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        sample_index=sample_index,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
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
    turn_id: str | None,
    flow_run_id: str | None,
    stage_id: str | None,
    question_key: str | None,
    modality: str,
    source_kind: str,
    source_ref_id: str | None,
    sample_id: str | None,
    inference_payload: dict[str, Any],
    captured_at: datetime | None,
    origin_flow_type: str | None = None,
) -> MultimodalInferenceResult:
    row = MultimodalInferenceResult(
        session_id=session_id,
        turn_id=turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        sample_id=sample_id,
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
    session.live_state_payload = _merge_live_payload(
        dict(session.live_state_payload or {}),
        *results,
    )
    session.updated_at = _utcnow()
    if session.status == "created":
        session.status = "active"


def _load_inference_payloads(
    db_session,
    *,
    session_id: str,
    modality: str,
    turn_id: str | None = None,
) -> list[dict[str, Any]]:
    statement = select(MultimodalInferenceResult).where(
        MultimodalInferenceResult.session_id == session_id,
        MultimodalInferenceResult.modality == modality,
    )
    if turn_id is not None:
        statement = statement.where(
            MultimodalInferenceResult.turn_id == turn_id
        )
    rows = db_session.execute(statement.order_by(MultimodalInferenceResult.created_at.asc())).scalars().all()
    return [dict(row.inference_payload or {}) for row in rows]


def _resolve_question_key(results_by_modality: dict[str, list[dict[str, Any]]]) -> str | None:
    for modality in ("speech", "text", "face", "pose"):
        rows = results_by_modality.get(modality) or []
        for row in reversed(rows):
            question_key = row.get("question_key")
            if question_key:
                return str(question_key)
    return None


def _build_turn_bundle_payload(
    db_session,
    session_id: str,
    turn_id: str,
    *,
    flow_run_id: str | None = None,
    origin_flow_type: str | None = None,
    stage_id: str | None = None,
    question_key: str | None = None,
    face_summary: dict[str, Any] | None = None,
    pose_summary: dict[str, Any] | None = None,
    visual_key_frames: list[dict[str, Any]] | None = None,
    visual_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    results_by_modality = {
        "speech": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="speech",
            turn_id=turn_id,
        ),
        "text": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="text",
            turn_id=turn_id,
        ),
        "face": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="face",
            turn_id=turn_id,
        ),
        "pose": _load_inference_payloads(
            db_session,
            session_id=session_id,
            modality="pose",
            turn_id=turn_id,
        ),
    }

    latest_speech = results_by_modality["speech"][-1] if results_by_modality["speech"] else None
    latest_text = results_by_modality["text"][-1] if results_by_modality["text"] else None
    resolved_face_summary = face_summary or _summarize_frame_payloads(
        "face",
        results_by_modality["face"],
        summary_type="turn_window",
    )
    resolved_pose_summary = pose_summary or _summarize_frame_payloads(
        "pose",
        results_by_modality["pose"],
        summary_type="turn_window",
    )

    return {
        "turn_id": turn_id,
        "session_id": session_id,
        "flow_run_id": flow_run_id,
        "origin_flow_type": origin_flow_type,
        "stage_id": stage_id,
        "question_key": question_key or _resolve_question_key(results_by_modality),
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
        "face_features": resolved_face_summary,
        "pose_features": resolved_pose_summary,
        "visual_key_frames": list(visual_key_frames or []),
        "visual_selection": dict(visual_selection or {}),
    }


def _upsert_turn_bundle(
    db_session,
    session_id: str,
    turn_id: str,
    *,
    flow_run_id: str | None = None,
    origin_flow_type: str | None = None,
    stage_id: str | None = None,
    question_key: str | None = None,
    face_summary: dict[str, Any] | None = None,
    pose_summary: dict[str, Any] | None = None,
    visual_key_frames: list[dict[str, Any]] | None = None,
    visual_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_payload = _build_turn_bundle_payload(
        db_session,
        session_id,
        turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        face_summary=face_summary,
        pose_summary=pose_summary,
        visual_key_frames=visual_key_frames,
        visual_selection=visual_selection,
    )
    now = _utcnow()
    incoming_is_finalized = _is_finalized_turn_bundle_payload(bundle_payload)
    insert_stmt = pg_insert(MultimodalTurnBundle).values(
        session_id=session_id,
        turn_id=turn_id,
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        stage_id=stage_id,
        question_key=question_key,
        bundle_payload=bundle_payload,
        created_at=now,
        updated_at=now,
    )
    update_values = {
        "flow_run_id": func.coalesce(
            insert_stmt.excluded.flow_run_id,
            MultimodalTurnBundle.flow_run_id,
        ),
        "origin_flow_type": func.coalesce(
            insert_stmt.excluded.origin_flow_type,
            MultimodalTurnBundle.origin_flow_type,
        ),
        "stage_id": func.coalesce(
            insert_stmt.excluded.stage_id,
            MultimodalTurnBundle.stage_id,
        ),
        "question_key": func.coalesce(
            insert_stmt.excluded.question_key,
            MultimodalTurnBundle.question_key,
        ),
        "bundle_payload": insert_stmt.excluded.bundle_payload,
        "updated_at": now,
    }
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[
            MultimodalTurnBundle.session_id,
            MultimodalTurnBundle.turn_id,
        ],
        set_=update_values,
    )
    if not incoming_is_finalized:
        # Preserve an already-finalized bundle when later non-finalized samples arrive.
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                MultimodalTurnBundle.session_id,
                MultimodalTurnBundle.turn_id,
            ],
            set_=update_values,
            where=text(
                "COALESCE((multimodal_turn_bundles.bundle_payload -> 'visual_selection' ->> 'persisted')::boolean, false) = false "
                "AND json_array_length(COALESCE(multimodal_turn_bundles.bundle_payload -> 'visual_key_frames', '[]'::json)) = 0"
            ),
        )
    result = db_session.execute(
        upsert_stmt.returning(MultimodalTurnBundle.bundle_payload)
    )
    persisted_payload = result.scalar_one_or_none()
    if persisted_payload is not None:
        return dict(persisted_payload or {})

    row = _load_turn_bundle_row(
        db_session,
        session_id=session_id,
        turn_id=turn_id,
    )
    if row is None:
        return dict(bundle_payload or {})
    return dict(row.bundle_payload or {})


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_turn_bundle_row(
    db_session,
    *,
    session_id: str,
    turn_id: str,
) -> MultimodalTurnBundle | None:
    return db_session.execute(
        select(MultimodalTurnBundle).where(
            MultimodalTurnBundle.session_id == session_id,
            MultimodalTurnBundle.turn_id == turn_id,
        )
    ).scalar_one_or_none()


def _is_finalized_turn_bundle_payload(bundle_payload: dict[str, Any] | None) -> bool:
    payload = dict(bundle_payload or {})
    visual_selection = dict(payload.get("visual_selection") or {})
    if bool(visual_selection.get("persisted")):
        return True
    return bool(payload.get("visual_key_frames"))


def _build_existing_finalized_turn_response(
    row: MultimodalTurnBundle,
    *,
    session_id: str,
    turn_id: str,
) -> dict[str, Any]:
    existing_selection = dict((row.bundle_payload or {}).get("visual_selection") or {})
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "status": "already_finalized",
        "finalized_at": existing_selection.get("persisted_at")
        or _isoformat(row.updated_at),
        "persisted": True,
        "source": "postgres_finalized_bundle",
        "turn_state": {
            "frame_count": existing_selection.get("frame_count"),
            "candidate_count": None,
            "last_sample_index": None,
            "last_updated_at": None,
        },
        "key_frame_selection": existing_selection,
        "turn_bundle": dict(row.bundle_payload or {}),
    }


def _build_visual_recovery_boundaries(
    *,
    finalized_bundle_present: bool,
) -> dict[str, Any]:
    return {
        "finalized_bundle_present": finalized_bundle_present,
        "recoverable_from_postgres": [
            "turn_bundle",
            "visual aggregate summary",
            "visual finalized state",
            "visual live face_pose snapshot",
        ]
        if finalized_bundle_present
        else [],
        "not_recoverable_from_postgres": [
            "full_frame_payloads",
            "candidate_pool",
            "pre_finalize_hot_state",
        ],
        "loss_boundary": (
            "unfinalized visual hot-state depends on Redis and may be lost if Redis restarts"
        ),
    }


def _build_key_frame_reference_payload(
    *,
    selected_frame_payload: dict[str, Any],
    visual_frame_id: str,
    face_capture_id: str,
    pose_capture_id: str,
) -> dict[str, Any]:
    return {
        **dict(selected_frame_payload or {}),
        "visual_frame_id": visual_frame_id,
        "face_capture_id": face_capture_id,
        "pose_capture_id": pose_capture_id,
    }


def _persist_selected_visual_key_frames(
    db_session,
    *,
    session_id: str,
    turn_id: str,
    flow_run_id: str | None,
    stage_id: str | None,
    question_key: str | None,
    frame_payloads_by_index: dict[int, dict[str, Any]],
    selected_frames: Sequence[dict[str, Any]],
    face_summary: dict[str, Any] | None,
    pose_summary: dict[str, Any] | None,
    strategy_version: str,
) -> list[dict[str, Any]]:
    persisted_key_frames: list[dict[str, Any]] = []
    for selected_frame in selected_frames:
        sample_index = int(selected_frame.get("sample_index") or 0)
        frame_payload = dict(frame_payloads_by_index.get(sample_index) or {})
        if not frame_payload:
            raise MultimodalServiceError(
                f"selected key frame payload missing for sample_index={sample_index}",
                5004,
                500,
            )

        sample_started_at = _parse_iso_datetime(frame_payload.get("sample_started_at"))
        sample_ended_at = _parse_iso_datetime(frame_payload.get("sample_ended_at"))
        visual_frame = _record_visual_frame(
            db_session,
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            stage_id=stage_id,
            question_key=question_key,
            sample_index=sample_index,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            mime_type=None,
            capture_payload={
                "source": "turn_finalize",
                "sample_index": sample_index,
                "sample_started_at": frame_payload.get("sample_started_at"),
                "sample_ended_at": frame_payload.get("sample_ended_at"),
                "selection_bucket": selected_frame.get("selection_bucket"),
                "selection_reasons": list(selected_frame.get("selection_reasons") or []),
                "selection_score": selected_frame.get("score"),
                "selection_strategy_version": strategy_version,
            },
            captured_at=sample_ended_at,
            storage_uri=frame_payload.get("storage_uri"),
            origin_flow_type=(
                str(frame_payload.get("origin_flow_type") or "").strip() or None
            ),
        )

        face_result = dict(frame_payload.get("face_result") or {})
        pose_result = dict(frame_payload.get("pose_result") or {})
        resolved_origin_flow_type = (
            str(frame_payload.get("origin_flow_type") or "").strip()
            or str(face_result.get("origin_flow_type") or "").strip()
            or str(pose_result.get("origin_flow_type") or "").strip()
            or None
        )
        if face_summary:
            face_result["sample_count"] = face_summary.get("sample_count")
            face_result["valid_sample_count"] = face_summary.get("valid_sample_count")
        if pose_summary:
            pose_result["sample_count"] = pose_summary.get("sample_count")
            pose_result["valid_sample_count"] = pose_summary.get("valid_sample_count")

        face_capture = _record_capture(
            db_session,
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            stage_id=stage_id,
            question_key=question_key,
            modality="face",
            capture_kind="frame",
            source_ref_id=visual_frame.id,
            sample_index=sample_index,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            capture_payload={
                "source": "turn_finalize",
                "visual_frame_id": visual_frame.id,
                "sample_index": sample_index,
                "sample_started_at": frame_payload.get("sample_started_at"),
                "sample_ended_at": frame_payload.get("sample_ended_at"),
                "selection_bucket": selected_frame.get("selection_bucket"),
                "selection_reasons": list(selected_frame.get("selection_reasons") or []),
                "selection_score": selected_frame.get("score"),
                "selection_strategy_version": strategy_version,
            },
            captured_at=sample_ended_at,
            origin_flow_type=resolved_origin_flow_type,
        )
        face_capture.storage_uri = frame_payload.get("storage_uri")
        db_session.add(face_capture)
        _record_inference_result(
            db_session,
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            stage_id=stage_id,
            question_key=question_key,
            modality="face",
            source_kind="frame",
            source_ref_id=visual_frame.id,
            sample_id=face_capture.id,
            inference_payload=face_result,
            captured_at=sample_ended_at,
            origin_flow_type=resolved_origin_flow_type,
        )

        pose_capture = _record_capture(
            db_session,
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            stage_id=stage_id,
            question_key=question_key,
            modality="pose",
            capture_kind="frame",
            source_ref_id=visual_frame.id,
            sample_index=sample_index,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            capture_payload={
                "source": "turn_finalize",
                "visual_frame_id": visual_frame.id,
                "sample_index": sample_index,
                "sample_started_at": frame_payload.get("sample_started_at"),
                "sample_ended_at": frame_payload.get("sample_ended_at"),
                "selection_bucket": selected_frame.get("selection_bucket"),
                "selection_reasons": list(selected_frame.get("selection_reasons") or []),
                "selection_score": selected_frame.get("score"),
                "selection_strategy_version": strategy_version,
            },
            captured_at=sample_ended_at,
            origin_flow_type=resolved_origin_flow_type,
        )
        pose_capture.storage_uri = frame_payload.get("storage_uri")
        db_session.add(pose_capture)
        _record_inference_result(
            db_session,
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            stage_id=stage_id,
            question_key=question_key,
            modality="pose",
            source_kind="frame",
            source_ref_id=visual_frame.id,
            sample_id=pose_capture.id,
            inference_payload=pose_result,
            captured_at=sample_ended_at,
            origin_flow_type=resolved_origin_flow_type,
        )

        persisted_key_frames.append(
            _build_key_frame_reference_payload(
                selected_frame_payload=selected_frame,
                visual_frame_id=visual_frame.id,
                face_capture_id=face_capture.id,
                pose_capture_id=pose_capture.id,
            )
        )
    return persisted_key_frames


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
        if not session_allows_flow_run(session, payload.flow_run_id):
            raise MultimodalServiceError("flow run mismatch", 4091, 409)
        resolved_origin_flow_type = _resolve_origin_flow_type(
            session,
            payload.origin_flow_type,
        )
        if payload.origin_flow_type != resolved_origin_flow_type:
            payload = payload.model_copy(
                update={"origin_flow_type": resolved_origin_flow_type}
            )

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
                turn_id=payload.turn_id,
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
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
            modality="audio",
            capture_kind="audio_turn",
            source_ref_id=payload.frame_id,
            sample_index=None,
            sample_started_at=payload.captured_at,
            sample_ended_at=payload.captured_at,
            capture_payload={
                "flow_run_id": payload.flow_run_id,
                "origin_flow_type": payload.origin_flow_type,
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
                assert resolved_audio_base64 is not None
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
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
            modality="speech",
            source_kind="audio_turn",
            source_ref_id=payload.frame_id,
            sample_id=None,
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
                turn_id=payload.turn_id,
                flow_run_id=payload.flow_run_id,
                origin_flow_type=payload.origin_flow_type,
                stage_id=payload.stage_id,
                question_key=payload.question_key,
                modality="text",
                source_kind="transcript_text",
                source_ref_id=payload.frame_id,
                sample_id=None,
                inference_payload=text_result,
                captured_at=captured_at,
            )

        _refresh_live_payload(session, *(result for result in [speech_result, text_result] if result is not None))
        db_session.add(session)
        db_session.flush()
        bundle_payload = _upsert_turn_bundle(
            db_session,
            session.id,
            payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
        )
        db_session.flush()
        db_session.refresh(session)
        _publish_multimodal_live_snapshot(session)
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
        image_bytes = payload.require_image_bytes()
        storage_uri = _build_frame_storage_uri(
            modality="face",
            session_id=session.id,
            turn_id=payload.turn_id,
            sample_index=payload.sample_index,
            image_format=payload.image_format,
            image_bytes=image_bytes,
        )
        return _submit_face_capture_with_session(
            db_session,
            session,
            payload,
            storage_uri=storage_uri,
            source_ref_id=str(payload.sample_index),
        )


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
        image_bytes = payload.require_image_bytes()
        storage_uri = _build_frame_storage_uri(
            modality="pose",
            session_id=session.id,
            turn_id=payload.turn_id,
            sample_index=payload.sample_index,
            image_format=payload.image_format,
            image_bytes=image_bytes,
        )
        return _submit_pose_capture_with_session(
            db_session,
            session,
            payload,
            storage_uri=storage_uri,
            source_ref_id=str(payload.sample_index),
        )


def submit_visual_capture(
    session_id: str,
    payload: SubmitFrameCaptureRequest,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        request_started_at = time.perf_counter()
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        if not session_allows_flow_run(session, payload.flow_run_id):
            raise MultimodalServiceError("flow run mismatch", 4091, 409)
        resolved_origin_flow_type = _resolve_origin_flow_type(
            session,
            payload.origin_flow_type,
        )
        if payload.origin_flow_type != resolved_origin_flow_type:
            payload = payload.model_copy(
                update={"origin_flow_type": resolved_origin_flow_type}
            )

        existing_response = _find_existing_visual_capture_response(
            db_session,
            session=session,
            payload=payload,
        )
        if existing_response is not None:
            logger.info(
                "visual capture idempotent reuse session_id=%s turn_id=%s sample_index=%s source=db",
                session.id,
                payload.turn_id,
                payload.sample_index,
            )
            return existing_response

        image_bytes = payload.require_image_bytes()
        image_bytes_length = len(image_bytes)
        visual_storage_future = _VISUAL_STORAGE_EXECUTOR.submit(
            _build_visual_frame_storage_uri,
            session_id=session.id,
            turn_id=payload.turn_id,
            sample_index=payload.sample_index,
            image_format=payload.image_format,
            image_bytes=image_bytes,
        )

        face_payload = payload.model_copy(
            update={"frame_id": payload.frame_id or f"face-{payload.sample_index}"}
        )
        pose_payload = payload.model_copy(
            update={"frame_id": payload.frame_id or f"pose-{payload.sample_index}"}
        )
        face_infer_started_at = time.perf_counter()
        face_result = _infer_face_capture_result(session.id, face_payload)
        face_infer_completed_at = time.perf_counter()
        pose_infer_started_at = time.perf_counter()
        pose_result = _infer_pose_capture_result(session.id, pose_payload)
        pose_infer_completed_at = time.perf_counter()

        storage_wait_started_at = time.perf_counter()
        visual_storage_uri = visual_storage_future.result()
        storage_wait_completed_at = time.perf_counter()
        redis_live_payload = _merge_live_payload(
            dict(session.live_state_payload or {}),
            face_result,
            pose_result,
        )
        redis_write_started_at = time.perf_counter()
        redis_write_result = write_visual_frame_state(
            session_id=session.id,
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id,
            question_key=payload.question_key,
            stage_id=payload.stage_id,
            sample_index=payload.sample_index,
            sample_started_at=payload.sample_started_at,
            sample_ended_at=payload.sample_ended_at,
            storage_uri=visual_storage_uri,
            face_result=face_result,
            pose_result=pose_result,
            live_payload=redis_live_payload,
        )
        redis_write_completed_at = time.perf_counter()
        coarse_checkpoint_due = bool(redis_write_result.coarse_checkpoint_due)
        coarse_checkpoint_applied = False
        if redis_write_result.coarse_checkpoint_due:
            logger.info(
                "visual turn coarse checkpoint due session_id=%s turn_id=%s sample_index=%s",
                session.id,
                payload.turn_id,
                payload.sample_index,
            )
        redis_turn_aggregate = redis_write_result.turn_aggregate_payload
        if redis_write_result.duplicate:
            logger.info(
                "visual capture duplicate redis hit session_id=%s turn_id=%s sample_index=%s",
                session.id,
                payload.turn_id,
                payload.sample_index,
            )
            existing_response = _find_existing_visual_capture_response(
                db_session,
                session=session,
                payload=payload,
            )
            if existing_response is not None:
                logger.info(
                    "visual capture idempotent reuse session_id=%s turn_id=%s sample_index=%s source=redis+db",
                    session.id,
                    payload.turn_id,
                    payload.sample_index,
                )
                return existing_response
        turn_bundle = _build_current_turn_bundle_from_redis(
            db_session,
            session_id=session.id,
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
            redis_turn_aggregate=redis_turn_aggregate,
        )
        if redis_write_result.success:
            checkpoint_started_at = time.perf_counter()
            if coarse_checkpoint_due:
                coarse_checkpoint_applied = _apply_visual_coarse_checkpoint(
                    db_session,
                    session=session,
                    payload=payload,
                    face_result=face_result,
                    pose_result=pose_result,
                    redis_turn_aggregate=redis_turn_aggregate,
                    redis_turn_state=redis_write_result.turn_state_payload,
                )
            checkpoint_completed_at = time.perf_counter()
            _apply_frame_summary_counts(
                face_result,
                modality="face",
                turn_bundle=turn_bundle,
                sample_index=payload.sample_index,
            )
            _apply_frame_summary_counts(
                pose_result,
                modality="pose",
                turn_bundle=turn_bundle,
                sample_index=payload.sample_index,
            )
            hot_path_completed_at = checkpoint_completed_at
            response_payload = _build_hot_path_visual_capture_response(
                session=session,
                payload=payload,
                storage_uri=visual_storage_uri,
                face_result=face_result,
                pose_result=pose_result,
                turn_bundle=turn_bundle,
                visual_pipeline=_build_visual_pipeline_status(
                    state_store="redis_hot",
                    live_state_source="redis",
                    turn_bundle_source="redis" if turn_bundle else "snapshot",
                    degraded=False,
                ),
            )
            _log_visual_capture_timing(
                session_id=session.id,
                turn_id=payload.turn_id,
                sample_index=payload.sample_index,
                image_bytes_length=image_bytes_length,
                face_result=face_result,
                pose_result=pose_result,
                storage_uri=visual_storage_uri,
                turn_bundle=turn_bundle,
                total_ms=_elapsed_ms(request_started_at, hot_path_completed_at),
                face_infer_ms=_elapsed_ms(face_infer_started_at, face_infer_completed_at),
                pose_infer_ms=_elapsed_ms(pose_infer_started_at, pose_infer_completed_at),
                inference_total_ms=_elapsed_ms(face_infer_started_at, pose_infer_completed_at),
                storage_wait_ms=_elapsed_ms(
                    storage_wait_started_at,
                    storage_wait_completed_at,
                ),
                redis_write_ms=_elapsed_ms(
                    redis_write_started_at,
                    redis_write_completed_at,
                ),
                redis_write_success=redis_write_result.success,
                persistence_ms=_elapsed_ms(
                    checkpoint_started_at,
                    checkpoint_completed_at,
                )
                if coarse_checkpoint_due
                else 0,
                coarse_checkpoint_due=coarse_checkpoint_due,
                coarse_checkpoint_applied=coarse_checkpoint_applied,
            )
            return response_payload
        persistence_started_at = time.perf_counter()
        visual_frame = _record_visual_frame(
            db_session,
            session_id=session.id,
            turn_id=payload.turn_id,
            flow_run_id=payload.flow_run_id,
            origin_flow_type=payload.origin_flow_type,
            stage_id=payload.stage_id,
            question_key=payload.question_key,
            sample_index=payload.sample_index,
            sample_started_at=payload.sample_started_at,
            sample_ended_at=payload.sample_ended_at,
            mime_type=payload.mime_type,
            capture_payload=_build_frame_capture_payload(payload),
            captured_at=payload.sample_ended_at,
            storage_uri=visual_storage_uri,
        )
        visual_frame_id = visual_frame.id
        face_capture_row = _record_frame_capture_result(
            db_session,
            session_id=session.id,
            payload=face_payload,
            modality="face",
            source_ref_id=visual_frame_id,
            storage_uri=visual_storage_uri,
            inference_payload=face_result,
            sample_id=visual_frame_id,
        )
        pose_capture_row = _record_frame_capture_result(
            db_session,
            session_id=session.id,
            payload=pose_payload,
            modality="pose",
            source_ref_id=visual_frame_id,
            storage_uri=visual_storage_uri,
            inference_payload=pose_result,
            sample_id=visual_frame_id,
        )

        if payload.turn_id:
            turn_bundle = _upsert_turn_bundle(
                db_session,
                session.id,
                payload.turn_id,
                flow_run_id=payload.flow_run_id,
                origin_flow_type=payload.origin_flow_type,
                stage_id=payload.stage_id,
                question_key=payload.question_key,
                face_summary=(redis_turn_aggregate or {}).get("face_features"),
                pose_summary=(redis_turn_aggregate or {}).get("pose_features"),
            )
        _apply_frame_summary_counts(
            face_result,
            modality="face",
            turn_bundle=turn_bundle,
            sample_index=payload.sample_index,
        )
        _apply_frame_summary_counts(
            pose_result,
            modality="pose",
            turn_bundle=turn_bundle,
            sample_index=payload.sample_index,
        )
        _refresh_live_payload(session, face_result, pose_result)
        db_session.add(session)
        db_session.flush()
        persistence_completed_at = time.perf_counter()
        db_session.refresh(session)
        _publish_multimodal_live_snapshot(
            session,
            redis_live_payload=redis_write_result.live_payload,
        )
        face_response = _build_frame_capture_response(
            capture_row=face_capture_row,
            session_id=session.id,
            question_key=payload.question_key,
            modality="face",
            result_payload=face_result,
            storage_uri=visual_storage_uri,
            turn_bundle=turn_bundle,
        )
        pose_response = _build_frame_capture_response(
            capture_row=pose_capture_row,
            session_id=session.id,
            question_key=payload.question_key,
            modality="pose",
            result_payload=pose_result,
            storage_uri=visual_storage_uri,
            turn_bundle=turn_bundle,
        )
        response_payload = _build_visual_capture_response(
            visual_frame=visual_frame,
            session=session,
            payload=payload,
            storage_uri=visual_storage_uri,
            face_response=face_response,
            pose_response=pose_response,
            turn_bundle=turn_bundle,
            visual_pipeline=_build_visual_pipeline_status(
                state_store="postgres_cold",
                live_state_source="postgres",
                turn_bundle_source="postgres" if turn_bundle else "snapshot",
                degraded=True,
                fallback_reason="redis_unavailable",
            ),
        )
        _log_visual_capture_timing(
            session_id=session.id,
            turn_id=payload.turn_id,
            sample_index=payload.sample_index,
            image_bytes_length=image_bytes_length,
            face_result=face_result,
            pose_result=pose_result,
            storage_uri=visual_storage_uri,
            turn_bundle=turn_bundle,
            total_ms=_elapsed_ms(request_started_at, persistence_completed_at),
            face_infer_ms=_elapsed_ms(face_infer_started_at, face_infer_completed_at),
            pose_infer_ms=_elapsed_ms(pose_infer_started_at, pose_infer_completed_at),
            inference_total_ms=_elapsed_ms(face_infer_started_at, pose_infer_completed_at),
            storage_wait_ms=_elapsed_ms(
                storage_wait_started_at,
                storage_wait_completed_at,
            ),
            redis_write_ms=_elapsed_ms(
                redis_write_started_at,
                redis_write_completed_at,
            ),
            redis_write_success=redis_write_result.success,
            persistence_ms=_elapsed_ms(
                persistence_started_at,
                persistence_completed_at,
            ),
            coarse_checkpoint_due=coarse_checkpoint_due,
            coarse_checkpoint_applied=coarse_checkpoint_applied,
        )
        return response_payload


def get_multimodal_live(session_id: str, acting_user_id: str | None = None) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        redis_live_payload = read_visual_live_payload(session.id)
        return _build_multimodal_live_response(
            session,
            redis_live_payload=redis_live_payload,
        )


def get_multimodal_turn_bundle(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        row = _load_turn_bundle_row(
            db_session,
            session_id=session.id,
            turn_id=turn_id,
        )
        if row is not None and _is_finalized_turn_bundle_payload(row.bundle_payload):
            return row.bundle_payload

        redis_turn_aggregate = read_visual_turn_aggregate_payload(session.id, turn_id)
        if redis_turn_aggregate is not None:
            return _build_turn_bundle_payload(
                db_session,
                session.id,
                turn_id,
                flow_run_id=str(
                    redis_turn_aggregate.get("flow_run_id") or session.flow_run_id or ""
                )
                or None,
                stage_id=str(redis_turn_aggregate.get("stage_id") or "").strip() or None,
                question_key=str(redis_turn_aggregate.get("question_key") or "").strip() or None,
                face_summary=(redis_turn_aggregate or {}).get("face_features"),
                pose_summary=(redis_turn_aggregate or {}).get("pose_features"),
            )

        if row is None:
            raise MultimodalServiceError("multimodal turn bundle not found", 4042, 404)
        return row.bundle_payload


def recover_multimodal_turn_hot_state(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        bundle_row = _load_turn_bundle_row(
            db_session,
            session_id=session.id,
            turn_id=turn_id,
        )
        if bundle_row is None or not _is_finalized_turn_bundle_payload(bundle_row.bundle_payload):
            return {
                "session_id": session.id,
                "turn_id": turn_id,
                "status": "not_recoverable",
                "recovery_applied": False,
                "recovery_source": None,
                "boundaries": _build_visual_recovery_boundaries(
                    finalized_bundle_present=False,
                ),
                "metrics": {
                    "redis_live_restored": False,
                    "redis_aggregate_restored": False,
                    "redis_state_restored": False,
                    "persisted_key_frame_count": 0,
                },
            }

        bundle_payload = dict(bundle_row.bundle_payload or {})
        visual_selection = dict(bundle_payload.get("visual_selection") or {})
        visual_key_frames = list(bundle_payload.get("visual_key_frames") or [])
        finalized_at = _parse_iso_datetime(visual_selection.get("persisted_at")) or bundle_row.updated_at
        recovered = recover_visual_turn_hot_state_from_bundle(
            session.id,
            turn_id,
            flow_run_id=bundle_row.flow_run_id,
            stage_id=bundle_row.stage_id,
            question_key=bundle_row.question_key,
            finalized_at=finalized_at,
            face_summary=dict(bundle_payload.get("face_features") or {}),
            pose_summary=dict(bundle_payload.get("pose_features") or {}),
            visual_key_frames=visual_key_frames,
            visual_selection=visual_selection,
        )
        if not recovered:
            raise MultimodalServiceError(
                "visual turn redis recovery unavailable",
                5032,
                503,
            )

        logger.info(
            "visual turn redis recovery applied session_id=%s turn_id=%s key_frames=%s",
            session.id,
            turn_id,
            len(visual_key_frames),
        )
        _publish_multimodal_live_snapshot(
            session,
            redis_live_payload=read_visual_live_payload(session.id),
        )
        return {
            "session_id": session.id,
            "turn_id": turn_id,
            "status": "recovered",
            "recovery_applied": True,
            "recovery_source": "postgres_finalized_bundle",
            "boundaries": _build_visual_recovery_boundaries(
                finalized_bundle_present=True,
            ),
            "metrics": {
                "redis_live_restored": True,
                "redis_aggregate_restored": True,
                "redis_state_restored": True,
                "persisted_key_frame_count": len(visual_key_frames),
                "recovered_at": _isoformat(_utcnow()),
            },
            "turn_bundle": bundle_payload,
        }


def finalize_multimodal_turn(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)

        existing_bundle_row = _load_turn_bundle_row(
            db_session,
            session_id=session.id,
            turn_id=turn_id,
        )
        if existing_bundle_row is not None and _is_finalized_turn_bundle_payload(
            existing_bundle_row.bundle_payload
        ):
            return _build_existing_finalized_turn_response(
                existing_bundle_row,
                session_id=session.id,
                turn_id=turn_id,
            )

        redis_turn_aggregate = read_visual_turn_aggregate_payload(session.id, turn_id)
        redis_turn_state = read_visual_turn_state_payload(session.id, turn_id)
        flow_run_id = None
        origin_flow_type = None
        stage_id = None
        question_key = None
        face_summary = None
        pose_summary = None
        frame_payloads: list[dict[str, Any]] = []
        candidate_payloads: list[dict[str, Any]] = []
        key_frame_selection: dict[str, Any]
        persisted_key_frames: list[dict[str, Any]]

        if redis_turn_aggregate is not None:
            flow_run_id = (
                str(redis_turn_aggregate.get("flow_run_id") or session.flow_run_id or "") or None
            )
            origin_flow_type = (
                str(redis_turn_aggregate.get("origin_flow_type") or "").strip() or None
            )
            stage_id = str(redis_turn_aggregate.get("stage_id") or "").strip() or None
            question_key = str(redis_turn_aggregate.get("question_key") or "").strip() or None
            face_summary = (redis_turn_aggregate or {}).get("face_features")
            pose_summary = (redis_turn_aggregate or {}).get("pose_features")

        if redis_turn_aggregate is not None and redis_turn_state is not None:
            frame_payloads = read_visual_turn_frame_payloads(
                session.id,
                turn_id,
                sample_indexes=redis_turn_state.get("all_frame_sample_indexes"),
            )
            if not frame_payloads:
                raise MultimodalServiceError("visual turn frame state not found", 4044, 404)
            candidate_payloads = read_visual_turn_candidate_payloads(
                session.id,
                turn_id,
                sample_indexes=redis_turn_state.get("candidate_sample_indexes"),
            )
            key_frame_selection = select_visual_key_frames(
                VisualKeyFrameSelectorInput(
                    frame_payloads=frame_payloads,
                    candidate_payloads=candidate_payloads,
                    turn_state_payload=redis_turn_state,
                    turn_aggregate_payload=redis_turn_aggregate,
                )
            ).to_payload()
            frame_payloads_by_index = {
                int(payload.get("sample_index") or 0): dict(payload) for payload in frame_payloads
            }
            if not origin_flow_type:
                for payload in frame_payloads:
                    origin_flow_type = (
                        str(payload.get("origin_flow_type") or "").strip()
                        or str((payload.get("face_result") or {}).get("origin_flow_type") or "").strip()
                        or str((payload.get("pose_result") or {}).get("origin_flow_type") or "").strip()
                        or None
                    )
                    if origin_flow_type:
                        break
            persisted_key_frames = _persist_selected_visual_key_frames(
                db_session,
                session_id=session.id,
                turn_id=turn_id,
                flow_run_id=flow_run_id,
                stage_id=stage_id,
                question_key=question_key,
                frame_payloads_by_index=frame_payloads_by_index,
                selected_frames=list(key_frame_selection.get("selected_frames") or []),
                face_summary=face_summary,
                pose_summary=pose_summary,
                strategy_version=str(key_frame_selection.get("strategy_version") or ""),
            )
        else:
            key_frame_selection = {
                "strategy_version": str(
                    get_settings()["visual_key_frame_strategy_version"]
                ),
                "frame_count": 0,
                "target_count": 0,
                "turn_duration_seconds": 0.0,
                "base_target_count": 0,
                "extra_time_coverage_count": 0,
                "applied_rules": ["no_visual_turn_state"],
                "selected_frames": [],
            }
            persisted_key_frames = []

        persisted_at = _isoformat(_utcnow())
        persisted_visual_selection = {
            **key_frame_selection,
            "persisted": True,
            "persisted_at": persisted_at,
            "selected_frames": persisted_key_frames,
        }
        try:
            turn_bundle = _upsert_turn_bundle(
                db_session,
                session.id,
                turn_id,
                flow_run_id=flow_run_id,
                origin_flow_type=origin_flow_type,
                stage_id=stage_id,
                question_key=question_key,
                face_summary=face_summary,
                pose_summary=pose_summary,
                visual_key_frames=persisted_key_frames,
                visual_selection=persisted_visual_selection,
            )
            db_session.flush()
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            existing_bundle_row = _load_turn_bundle_row(
                db_session,
                session_id=session.id,
                turn_id=turn_id,
            )
            if existing_bundle_row is None:
                raise
            return _build_existing_finalized_turn_response(
                existing_bundle_row,
                session_id=session.id,
                turn_id=turn_id,
            )
        redis_hot_state_cleaned = finalize_visual_turn_hot_state(
            session.id,
            turn_id,
            finalized_at=_parse_iso_datetime(persisted_at) or _utcnow(),
            persisted_key_frame_count=len(persisted_key_frames),
        )
        if not redis_hot_state_cleaned:
            logger.warning(
                "visual redis finalize cleanup skipped or failed session_id=%s turn_id=%s",
                session.id,
                turn_id,
            )
        try:
            pose_runtime_cleared = runtime_store.clear_pose_turn_state(session.id, turn_id)
        except Exception:
            logger.warning(
                "pose runtime clear failed after finalize session_id=%s turn_id=%s",
                session.id,
                turn_id,
                exc_info=True,
            )
            pose_runtime_cleared = False
        return {
            "session_id": session.id,
            "turn_id": turn_id,
            "status": "finalized",
            "finalized_at": persisted_at,
            "persisted": True,
            "source": "postgres_finalized_bundle",
            "turn_state": {
                "frame_count": int((redis_turn_state or {}).get("frame_count") or len(frame_payloads)),
                "candidate_count": len(candidate_payloads),
                "last_sample_index": (redis_turn_state or {}).get("last_sample_index"),
                "last_updated_at": (redis_turn_state or {}).get("last_updated_at"),
            },
            "redis_hot_state_cleaned": redis_hot_state_cleaned,
            "pose_runtime_cleared": pose_runtime_cleared,
            "key_frame_selection": persisted_visual_selection,
            "turn_bundle": turn_bundle,
        }


def clear_pose_turn_runtime_state(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None = None,
) -> dict[str, Any]:
    with get_db_session() as db_session:
        session = db_session.get(MultimodalSession, session_id)
        if session is None:
            raise MultimodalServiceError("multimodal session not found", 4041, 404)
        _ensure_session_access(session, acting_user_id)
        cleared = runtime_store.clear_pose_turn_state(session.id, turn_id)
        return {
            "session_id": session.id,
            "turn_id": turn_id,
            "modality": "pose",
            "cleared": cleared,
        }
