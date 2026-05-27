from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from app.config import get_settings
from app.redis import build_redis_key, get_optional_redis_client

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VisualFrameStateWriteResult:
    success: bool
    duplicate: bool = False
    coarse_checkpoint_due: bool = False
    live_payload: dict[str, Any] | None = None
    frame_payload: dict[str, Any] | None = None
    turn_aggregate_payload: dict[str, Any] | None = None
    turn_state_payload: dict[str, Any] | None = None
    candidate_payload: dict[str, Any] | None = None


def _isoformat(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw_value: bytes | str | None) -> dict[str, Any] | None:
    if raw_value in (None, b"", ""):
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8")
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _parse_datetime(value: Any) -> datetime | None:
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


def _copy_distribution_labels(
    labels: Sequence[dict[str, Any]] | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for item in labels or []:
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        score = item.get("ratio")
        if score in (None, ""):
            score = item.get("score")
        copied.append({"label": label, "score": float(score or 0.0)})
        if len(copied) >= limit:
            break
    return copied


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
        distribution[key] = {"count": positive_count, "ratio": ratio}
    return distribution


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

    sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    distribution = [
        {
            "label": label,
            "count": count,
            "ratio": round(count / valid_sample_count, 4),
        }
        for label, count in sorted_items
    ]
    return distribution, distribution[0]["label"], distribution[0]["ratio"], valid_sample_count


def _build_empty_modality_stats(modality: str) -> dict[str, Any]:
    return {
        "sample_count": 0,
        "valid_sample_count": 0,
        "label_counts": {},
        "quality_counts": {key: 0 for key in _resolve_frame_quality_keys(modality)},
    }


def _increment_modality_stats(
    stats: dict[str, Any] | None,
    payload: dict[str, Any],
    modality: str,
) -> dict[str, Any]:
    next_stats = dict(stats or _build_empty_modality_stats(modality))
    next_stats["sample_count"] = int(next_stats.get("sample_count") or 0) + 1

    label_counts = {
        str(label): int(count)
        for label, count in dict(next_stats.get("label_counts") or {}).items()
        if str(label).strip()
    }
    label = _extract_distribution_label(payload, modality)
    if label:
        label_counts[label] = label_counts.get(label, 0) + 1
        next_stats["valid_sample_count"] = int(next_stats.get("valid_sample_count") or 0) + 1
    else:
        next_stats["valid_sample_count"] = int(next_stats.get("valid_sample_count") or 0)
    next_stats["label_counts"] = label_counts

    quality_counts = {
        key: int(value or 0)
        for key, value in dict(next_stats.get("quality_counts") or {}).items()
    }
    quality_flags = dict(payload.get("quality_flags") or {})
    for key in _resolve_frame_quality_keys(modality):
        quality_counts.setdefault(key, 0)
        if bool(quality_flags.get(key)):
            quality_counts[key] += 1
    next_stats["quality_counts"] = quality_counts
    return next_stats


def _build_features_from_stats(stats: dict[str, Any] | None, modality: str) -> dict[str, Any]:
    normalized_stats = dict(stats or _build_empty_modality_stats(modality))
    sample_count = int(normalized_stats.get("sample_count") or 0)
    valid_sample_count = int(normalized_stats.get("valid_sample_count") or 0)
    label_counts = {
        str(label): int(count)
        for label, count in dict(normalized_stats.get("label_counts") or {}).items()
        if str(label).strip()
    }
    if valid_sample_count > 0:
        sorted_items = sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))
        label_distribution = [
            {
                "label": label,
                "count": count,
                "ratio": round(count / valid_sample_count, 4),
            }
            for label, count in sorted_items
        ]
        primary_label = label_distribution[0]["label"]
        primary_ratio = label_distribution[0]["ratio"]
    else:
        label_distribution = []
        primary_label = None
        primary_ratio = None

    quality_counts = {
        key: int(value or 0)
        for key, value in dict(normalized_stats.get("quality_counts") or {}).items()
    }
    quality_distribution = {
        key: {
            "count": quality_counts.get(key, 0),
            "ratio": round(quality_counts.get(key, 0) / sample_count, 4) if sample_count > 0 else 0.0,
        }
        for key in _resolve_frame_quality_keys(modality)
    }
    return {
        "summary_type": "turn_window",
        "primary_label": primary_label,
        "primary_score": primary_ratio,
        "primary_ratio": primary_ratio,
        "sample_count": sample_count,
        "valid_sample_count": valid_sample_count,
        "label_distribution": label_distribution,
        "quality_distribution": quality_distribution,
        "quality_flags": {
            f"{key}_ratio": quality_distribution[key]["ratio"] for key in quality_distribution
        },
    }


def _summarize_frame_payloads(
    modality: str,
    payloads: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if not payloads:
        return {
            "summary_type": "turn_window",
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

    label_distribution, primary_label, primary_ratio, valid_sample_count = _build_label_distribution(
        payloads,
        modality,
    )
    quality_distribution = _build_quality_distribution(payloads, modality)
    return {
        "summary_type": "turn_window",
        "primary_label": primary_label,
        "primary_score": primary_ratio,
        "primary_ratio": primary_ratio,
        "sample_count": len(payloads),
        "valid_sample_count": valid_sample_count,
        "label_distribution": label_distribution,
        "quality_distribution": quality_distribution,
        "quality_flags": {
            f"{key}_ratio": quality_distribution[key]["ratio"] for key in quality_distribution
        },
    }


def _derive_stats_from_payloads(payloads: Sequence[dict[str, Any]], modality: str) -> dict[str, Any]:
    stats = _build_empty_modality_stats(modality)
    for payload in payloads:
        stats = _increment_modality_stats(stats, payload, modality)
    return stats


def _normalize_result_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "modality": str(payload.get("modality") or "").strip(),
        "status": payload.get("status"),
        "processing_status": payload.get("processing_status"),
        "primary_label": payload.get("primary_label"),
        "primary_score": payload.get("primary_score"),
        "top_3_labels": _copy_labels(payload.get("top_3_labels")),
        "quality_flags": dict(payload.get("quality_flags") or {}),
        "sample_started_at": payload.get("sample_started_at"),
        "sample_ended_at": payload.get("sample_ended_at"),
        "sample_count": payload.get("sample_count"),
        "valid_sample_count": payload.get("valid_sample_count"),
        "error_message": payload.get("error_message"),
    }


def _normalize_turn_id(turn_id: str | None) -> str:
    normalized = str(turn_id or "").strip()
    return normalized or "unbound"


def build_visual_live_key(session_id: str) -> str:
    return build_redis_key("visual", "live", session_id)


def build_visual_turn_aggregate_key(session_id: str, turn_id: str | None) -> str:
    return build_redis_key("visual", "turn", session_id, _normalize_turn_id(turn_id), "aggregate")


def build_visual_turn_frame_key(
    session_id: str,
    turn_id: str | None,
    sample_index: int,
) -> str:
    return build_redis_key(
        "visual",
        "turn",
        session_id,
        _normalize_turn_id(turn_id),
        "frame",
        str(sample_index),
    )


def build_visual_turn_candidate_key(
    session_id: str,
    turn_id: str | None,
    sample_index: int,
) -> str:
    return build_redis_key(
        "visual",
        "turn",
        session_id,
        _normalize_turn_id(turn_id),
        "candidate",
        str(sample_index),
    )


def build_visual_turn_state_key(session_id: str, turn_id: str | None) -> str:
    return build_redis_key("visual", "turn", session_id, _normalize_turn_id(turn_id), "state")


def _read_visual_payload(key: str) -> dict[str, Any] | None:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning("visual redis client initialization failed for key=%s", key, exc_info=True)
        return None

    if client is None:
        return None

    try:
        return _json_loads(client.get(key))
    except Exception:
        logger.warning("visual redis read failed for key=%s", key, exc_info=True)
        return None


def read_visual_live_payload(session_id: str) -> dict[str, Any] | None:
    return _read_visual_payload(build_visual_live_key(session_id))


def read_visual_turn_aggregate_payload(
    session_id: str,
    turn_id: str | None,
) -> dict[str, Any] | None:
    return _read_visual_payload(build_visual_turn_aggregate_key(session_id, turn_id))


def read_visual_turn_state_payload(
    session_id: str,
    turn_id: str | None,
) -> dict[str, Any] | None:
    return _read_visual_payload(build_visual_turn_state_key(session_id, turn_id))


def _read_visual_payloads(keys: Sequence[str]) -> list[dict[str, Any]]:
    normalized_keys = [key for key in keys if str(key).strip()]
    if not normalized_keys:
        return []
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning("visual redis client initialization failed for batch read", exc_info=True)
        return []

    if client is None:
        return []

    try:
        raw_values = client.mget(normalized_keys)
    except Exception:
        logger.warning("visual redis batch read failed for %s keys", len(normalized_keys), exc_info=True)
        return []

    payloads: list[dict[str, Any]] = []
    for raw_value in raw_values:
        payload = _json_loads(raw_value)
        if payload is not None:
            payloads.append(payload)
    return payloads


def read_visual_turn_frame_payloads(
    session_id: str,
    turn_id: str | None,
    *,
    sample_indexes: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    if sample_indexes is None:
        state_payload = read_visual_turn_state_payload(session_id, turn_id) or {}
        sample_indexes = list(state_payload.get("all_frame_sample_indexes") or [])
    keys = [
        build_visual_turn_frame_key(session_id, turn_id, int(sample_index))
        for sample_index in sample_indexes or []
        if int(sample_index) > 0
    ]
    payloads = _read_visual_payloads(keys)
    return sorted(payloads, key=lambda payload: int(payload.get("sample_index") or 0))


def read_visual_turn_candidate_payloads(
    session_id: str,
    turn_id: str | None,
    *,
    sample_indexes: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    if sample_indexes is None:
        state_payload = read_visual_turn_state_payload(session_id, turn_id) or {}
        sample_indexes = list(state_payload.get("candidate_sample_indexes") or [])
    keys = [
        build_visual_turn_candidate_key(session_id, turn_id, int(sample_index))
        for sample_index in sample_indexes or []
        if int(sample_index) > 0
    ]
    payloads = _read_visual_payloads(keys)
    return sorted(payloads, key=lambda payload: int(payload.get("sample_index") or 0))


def mark_visual_turn_coarse_checkpoint(
    session_id: str,
    turn_id: str | None,
    *,
    checkpointed_at: datetime,
    checkpoint_frame_count: int,
    retained_frame_sample_indexes: Sequence[int],
    checkpoint_key_frame_sample_indexes: Sequence[int],
    retained_candidate_sample_indexes: Sequence[int],
) -> bool:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning(
            "visual redis client initialization failed for checkpoint mark session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False

    if client is None:
        return False

    settings = get_settings()
    state_key = build_visual_turn_state_key(session_id, turn_id)
    try:
        state_payload = _json_loads(client.get(state_key))
        if state_payload is None:
            return False
        retained_frame_indexes = sorted(
            {int(value) for value in retained_frame_sample_indexes if int(value) > 0}
        )
        retained_candidate_indexes = sorted(
            {int(value) for value in retained_candidate_sample_indexes if int(value) > 0}
        )
        checkpoint_key_frame_indexes = sorted(
            {int(value) for value in checkpoint_key_frame_sample_indexes if int(value) > 0}
        )
        previous_frame_indexes = sorted(
            {int(value) for value in list(state_payload.get("all_frame_sample_indexes") or [])}
        )
        previous_candidate_indexes = sorted(
            {int(value) for value in list(state_payload.get("candidate_sample_indexes") or [])}
        )
        checkpoint_count = int(state_payload.get("checkpoint_count") or 0) + 1
        next_state_payload = {
            **dict(state_payload),
            "last_checkpoint_at": _isoformat(checkpointed_at),
            "coarse_checkpoint_due": False,
            "checkpoint_count": checkpoint_count,
            "last_checkpoint_frame_count": checkpoint_frame_count,
            "checkpoint_key_frame_sample_indexes": checkpoint_key_frame_indexes,
            "all_frame_sample_indexes": retained_frame_indexes,
            "candidate_sample_indexes": retained_candidate_indexes,
            "recent_frame_sample_indexes": [
                int(value)
                for value in list(state_payload.get("recent_frame_sample_indexes") or [])
                if int(value) in set(retained_frame_indexes)
            ],
            "next_checkpoint_due_at": _isoformat(
                checkpointed_at
                + timedelta(
                    seconds=max(
                        15,
                        int(settings["visual_turn_subsequent_checkpoint_interval_seconds"]),
                    )
                )
            ),
        }
        pipeline = client.pipeline(transaction=False)
        pipeline.set(
            state_key,
            _json_dumps(next_state_payload),
            ex=int(settings["visual_turn_state_ttl_seconds"]),
        )
        for sample_index in previous_frame_indexes:
            if sample_index not in set(retained_frame_indexes):
                pipeline.delete(build_visual_turn_frame_key(session_id, turn_id, sample_index))
        for sample_index in previous_candidate_indexes:
            if sample_index not in set(retained_candidate_indexes):
                pipeline.delete(build_visual_turn_candidate_key(session_id, turn_id, sample_index))
        pipeline.execute()
        return True
    except Exception:
        logger.warning(
            "visual redis checkpoint mark failed session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False


def finalize_visual_turn_hot_state(
    session_id: str,
    turn_id: str | None,
    *,
    finalized_at: datetime,
    persisted_key_frame_count: int,
) -> bool:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning(
            "visual redis client initialization failed for finalize cleanup session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False

    if client is None:
        return False

    settings = get_settings()
    aggregate_key = build_visual_turn_aggregate_key(session_id, turn_id)
    state_key = build_visual_turn_state_key(session_id, turn_id)
    try:
        aggregate_payload = _json_loads(client.get(aggregate_key))
        state_payload = _json_loads(client.get(state_key))
        if aggregate_payload is None and state_payload is None:
            return False

        all_frame_indexes = list((state_payload or {}).get("all_frame_sample_indexes") or [])
        candidate_indexes = list((state_payload or {}).get("candidate_sample_indexes") or [])
        finalized_at_iso = _isoformat(finalized_at)

        next_aggregate_payload = {
            **dict(aggregate_payload or {}),
            "status": "finalized",
            "finalized_at": finalized_at_iso,
            "persisted_key_frame_count": persisted_key_frame_count,
        }
        next_state_payload = {
            **dict(state_payload or {}),
            "status": "finalized",
            "finalized_at": finalized_at_iso,
            "finalized_key_frame_count": persisted_key_frame_count,
            "coarse_checkpoint_due": False,
            "candidate_sample_indexes": [],
            "recent_frame_sample_indexes": [],
            "last_checkpoint_at": (state_payload or {}).get("last_checkpoint_at")
            or finalized_at_iso,
            "next_checkpoint_due_at": None,
        }

        pipeline = client.pipeline(transaction=False)
        pipeline.set(
            aggregate_key,
            _json_dumps(next_aggregate_payload),
            ex=int(settings["visual_turn_finalized_aggregate_ttl_seconds"]),
        )
        pipeline.set(
            state_key,
            _json_dumps(next_state_payload),
            ex=int(settings["visual_turn_finalized_state_ttl_seconds"]),
        )
        for sample_index in all_frame_indexes:
            pipeline.delete(build_visual_turn_frame_key(session_id, turn_id, int(sample_index)))
        for sample_index in candidate_indexes:
            pipeline.delete(build_visual_turn_candidate_key(session_id, turn_id, int(sample_index)))
        pipeline.execute()
        return True
    except Exception:
        logger.warning(
            "visual redis finalize cleanup failed session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False


def recover_visual_turn_hot_state_from_bundle(
    session_id: str,
    turn_id: str | None,
    *,
    flow_run_id: str | None,
    stage_id: str | None,
    question_key: str | None,
    finalized_at: datetime,
    face_summary: dict[str, Any] | None,
    pose_summary: dict[str, Any] | None,
    visual_key_frames: Sequence[dict[str, Any]],
    visual_selection: dict[str, Any] | None,
) -> bool:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning(
            "visual redis client initialization failed for recovery session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False

    if client is None:
        return False

    settings = get_settings()
    finalized_at_iso = _isoformat(finalized_at)
    finalized_key_frame_indexes = sorted(
        {
            int(item.get("sample_index") or 0)
            for item in visual_key_frames
            if int(item.get("sample_index") or 0) > 0
        }
    )
    face_stats = _build_stats_from_summary(face_summary, "face")
    pose_stats = _build_stats_from_summary(pose_summary, "pose")

    aggregate_payload = {
        "session_id": session_id,
        "turn_id": turn_id,
        "flow_run_id": flow_run_id,
        "question_key": question_key,
        "stage_id": stage_id,
        "status": "finalized",
        "recovered_from_postgres": True,
        "finalized_at": finalized_at_iso,
        "updated_at": finalized_at_iso,
        "last_sample_index": max(finalized_key_frame_indexes) if finalized_key_frame_indexes else None,
        "last_sample_started_at": None,
        "last_sample_ended_at": finalized_at_iso,
        "face_latest": _build_live_modality_from_summary(
            face_summary,
            modality="face",
            captured_at=finalized_at_iso,
        ),
        "pose_latest": _build_live_modality_from_summary(
            pose_summary,
            modality="pose",
            captured_at=finalized_at_iso,
        ),
        "face_stats": face_stats,
        "pose_stats": pose_stats,
        "face_features": dict(face_summary or {}),
        "pose_features": dict(pose_summary or {}),
        "persisted_key_frame_count": len(finalized_key_frame_indexes),
    }
    state_payload = {
        "session_id": session_id,
        "turn_id": turn_id,
        "flow_run_id": flow_run_id,
        "question_key": question_key,
        "stage_id": stage_id,
        "status": "finalized",
        "recovered_from_postgres": True,
        "recovery_scope": "finalized_bundle_only",
        "first_sample_started_at": None,
        "last_sample_index": max(finalized_key_frame_indexes) if finalized_key_frame_indexes else None,
        "frame_count": int((visual_selection or {}).get("frame_count") or 0),
        "all_frame_sample_indexes": [],
        "checkpoint_key_frame_sample_indexes": finalized_key_frame_indexes,
        "recent_frame_sample_indexes": [],
        "candidate_sample_indexes": [],
        "finalized_key_frame_sample_indexes": finalized_key_frame_indexes,
        "finalized_key_frame_count": len(finalized_key_frame_indexes),
        "last_face_label": dict(face_summary or {}).get("primary_label"),
        "last_pose_label": dict(pose_summary or {}).get("primary_label"),
        "last_updated_at": finalized_at_iso,
        "last_checkpoint_at": finalized_at_iso,
        "last_checkpoint_frame_count": int((visual_selection or {}).get("frame_count") or 0),
        "checkpoint_count": max(1, int((visual_selection or {}).get("checkpoint_count") or 1)),
        "frames_since_last_checkpoint": 0,
        "coarse_checkpoint_due": False,
        "checkpoint_interval_seconds": max(
            15,
            int(settings["visual_turn_subsequent_checkpoint_interval_seconds"]),
        ),
        "checkpoint_min_frame_count": max(
            1,
            int(settings["visual_turn_subsequent_checkpoint_min_frame_count"]),
        ),
        "next_checkpoint_due_at": None,
        "finalized_at": finalized_at_iso,
        "unrecoverable_state": [
            "frame_payloads",
            "candidate_payloads",
            "pre_finalize_runtime",
        ],
    }
    live_payload = {
        "session_id": session_id,
        "updated_at": finalized_at_iso,
        "face": _build_live_modality_from_summary(
            face_summary,
            modality="face",
            captured_at=finalized_at_iso,
        ),
        "pose": _build_live_modality_from_summary(
            pose_summary,
            modality="pose",
            captured_at=finalized_at_iso,
        ),
    }

    try:
        pipeline = client.pipeline(transaction=False)
        pipeline.set(
            build_visual_live_key(session_id),
            _json_dumps(live_payload),
            ex=int(settings["visual_live_ttl_seconds"]),
        )
        pipeline.set(
            build_visual_turn_aggregate_key(session_id, turn_id),
            _json_dumps(aggregate_payload),
            ex=int(settings["visual_turn_finalized_aggregate_ttl_seconds"]),
        )
        pipeline.set(
            build_visual_turn_state_key(session_id, turn_id),
            _json_dumps(state_payload),
            ex=int(settings["visual_turn_finalized_state_ttl_seconds"]),
        )
        pipeline.execute()
        return True
    except Exception:
        logger.warning(
            "visual redis recovery write failed session_id=%s turn_id=%s",
            session_id,
            turn_id,
            exc_info=True,
        )
        return False


def _normalize_existing_modality_stats(
    aggregate_payload: dict[str, Any] | None,
    modality: str,
) -> dict[str, Any]:
    if aggregate_payload is None:
        return _build_empty_modality_stats(modality)
    stats_key = f"{modality}_stats"
    if isinstance(aggregate_payload.get(stats_key), dict):
        return {
            **_build_empty_modality_stats(modality),
            **dict(aggregate_payload.get(stats_key) or {}),
        }
    legacy_samples = list((aggregate_payload or {}).get(f"{modality}_samples") or [])
    return _derive_stats_from_payloads(legacy_samples, modality)


def _build_stats_from_summary(
    summary: dict[str, Any] | None,
    modality: str,
) -> dict[str, Any]:
    normalized_summary = dict(summary or {})
    label_counts = {
        str(item.get("label") or "").strip(): int(item.get("count") or 0)
        for item in list(normalized_summary.get("label_distribution") or [])
        if str(item.get("label") or "").strip()
    }
    quality_counts = {
        key: int((dict(normalized_summary.get("quality_distribution") or {}).get(key) or {}).get("count") or 0)
        for key in _resolve_frame_quality_keys(modality)
    }
    return {
        "sample_count": int(normalized_summary.get("sample_count") or 0),
        "valid_sample_count": int(normalized_summary.get("valid_sample_count") or 0),
        "label_counts": label_counts,
        "quality_counts": quality_counts,
    }


def _build_live_modality_from_summary(
    summary: dict[str, Any] | None,
    *,
    modality: str,
    captured_at: str | None,
) -> dict[str, Any]:
    normalized_summary = dict(summary or {})
    return {
        "status": "completed",
        "processing_status": "completed",
        "primary_label": normalized_summary.get("primary_label"),
        "primary_score": normalized_summary.get("primary_score"),
        "top_3_labels": _copy_distribution_labels(normalized_summary.get("label_distribution")),
        "quality_flags": dict(normalized_summary.get("quality_flags") or {}),
        "latest_capture_at": captured_at,
        "sample_count": normalized_summary.get("sample_count"),
        "valid_sample_count": normalized_summary.get("valid_sample_count"),
        "error_message": None,
        "modality": modality,
    }


def _build_frame_payload(
    *,
    session_id: str,
    turn_id: str | None,
    flow_run_id: str,
    question_key: str,
    stage_id: str | None,
    sample_index: int,
    sample_started_at: datetime,
    sample_ended_at: datetime,
    storage_uri: str | None,
    face_result: dict[str, Any],
    pose_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "flow_run_id": flow_run_id,
        "question_key": question_key,
        "stage_id": stage_id,
        "sample_index": sample_index,
        "sample_started_at": _isoformat(sample_started_at),
        "sample_ended_at": _isoformat(sample_ended_at),
        "storage_uri": storage_uri,
        "face_result": _normalize_result_payload(face_result),
        "pose_result": _normalize_result_payload(pose_result),
    }


def _build_live_payload(
    *,
    session_id: str,
    updated_at: datetime,
    live_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "updated_at": _isoformat(updated_at),
        **dict(live_payload or {}),
    }


def _build_candidate_payload(
    *,
    aggregate_payload: dict[str, Any] | None,
    frame_payload: dict[str, Any],
) -> dict[str, Any] | None:
    reasons: list[str] = []
    sample_index = int(frame_payload["sample_index"])
    face_result = dict(frame_payload["face_result"] or {})
    pose_result = dict(frame_payload["pose_result"] or {})

    if sample_index <= 1:
        reasons.append("first_frame")
    if str(face_result.get("processing_status") or "").lower() == "failed":
        reasons.append("face_failed")
    if str(pose_result.get("processing_status") or "").lower() == "failed":
        reasons.append("pose_failed")
    for key, value in dict(face_result.get("quality_flags") or {}).items():
        if bool(value):
            reasons.append(f"face_{key}")
    for key, value in dict(pose_result.get("quality_flags") or {}).items():
        if bool(value):
            reasons.append(f"pose_{key}")

    previous_face_label = str(
        ((aggregate_payload or {}).get("face_latest") or {}).get("primary_label") or ""
    ).strip()
    current_face_label = str(face_result.get("primary_label") or "").strip()
    if previous_face_label and current_face_label and current_face_label != previous_face_label:
        reasons.append("face_label_changed")

    previous_pose_label = str(
        ((aggregate_payload or {}).get("pose_latest") or {}).get("primary_label") or ""
    ).strip()
    current_pose_label = str(pose_result.get("primary_label") or "").strip()
    if previous_pose_label and current_pose_label and current_pose_label != previous_pose_label:
        reasons.append("pose_label_changed")

    if not reasons:
        return None

    return {
        "session_id": frame_payload["session_id"],
        "turn_id": frame_payload["turn_id"],
        "flow_run_id": frame_payload["flow_run_id"],
        "question_key": frame_payload["question_key"],
        "stage_id": frame_payload["stage_id"],
        "sample_index": sample_index,
        "sample_ended_at": frame_payload["sample_ended_at"],
        "storage_uri": frame_payload["storage_uri"],
        "reasons": reasons,
        "score": len(reasons),
        "face_result": face_result,
        "pose_result": pose_result,
    }


def _build_turn_aggregate_payload(
    *,
    aggregate_payload: dict[str, Any] | None,
    frame_payload: dict[str, Any],
) -> dict[str, Any]:
    face_stats = _increment_modality_stats(
        _normalize_existing_modality_stats(aggregate_payload, "face"),
        dict(frame_payload["face_result"] or {}),
        "face",
    )
    pose_stats = _increment_modality_stats(
        _normalize_existing_modality_stats(aggregate_payload, "pose"),
        dict(frame_payload["pose_result"] or {}),
        "pose",
    )

    return {
        "session_id": frame_payload["session_id"],
        "turn_id": frame_payload["turn_id"],
        "flow_run_id": frame_payload["flow_run_id"],
        "question_key": frame_payload["question_key"],
        "stage_id": frame_payload["stage_id"],
        "updated_at": frame_payload["sample_ended_at"],
        "last_sample_index": frame_payload["sample_index"],
        "last_sample_started_at": frame_payload["sample_started_at"],
        "last_sample_ended_at": frame_payload["sample_ended_at"],
        "face_latest": dict(frame_payload["face_result"] or {}),
        "pose_latest": dict(frame_payload["pose_result"] or {}),
        "face_stats": face_stats,
        "pose_stats": pose_stats,
        "face_features": _build_features_from_stats(face_stats, "face"),
        "pose_features": _build_features_from_stats(pose_stats, "pose"),
    }


def _build_turn_state_payload(
    *,
    state_payload: dict[str, Any] | None,
    frame_payload: dict[str, Any],
    candidate_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    settings = get_settings()
    first_sample_started_at = (
        str((state_payload or {}).get("first_sample_started_at") or "").strip()
        or str(frame_payload["sample_started_at"])
    )
    frame_count = int((state_payload or {}).get("frame_count") or 0) + 1
    all_frame_indexes = list((state_payload or {}).get("all_frame_sample_indexes") or [])
    all_frame_indexes.append(int(frame_payload["sample_index"]))
    all_frame_indexes = sorted({int(value) for value in all_frame_indexes})
    checkpoint_key_frame_indexes = list(
        (state_payload or {}).get("checkpoint_key_frame_sample_indexes") or []
    )
    checkpoint_key_frame_indexes = sorted({int(value) for value in checkpoint_key_frame_indexes})

    candidate_indexes = list((state_payload or {}).get("candidate_sample_indexes") or [])
    if candidate_payload is not None:
        candidate_indexes.append(int(candidate_payload["sample_index"]))
    candidate_indexes = sorted({int(value) for value in candidate_indexes})
    candidate_limit = max(1, int(settings["visual_turn_candidate_limit"]))
    if len(candidate_indexes) > candidate_limit:
        candidate_indexes = candidate_indexes[-candidate_limit:]

    recent_frame_indexes = list((state_payload or {}).get("recent_frame_sample_indexes") or [])
    recent_frame_indexes.append(int(frame_payload["sample_index"]))
    recent_frame_indexes = sorted({int(value) for value in recent_frame_indexes})
    recent_frame_limit = max(1, int(settings["visual_turn_recent_frame_limit"]))
    if len(recent_frame_indexes) > recent_frame_limit:
        recent_frame_indexes = recent_frame_indexes[-recent_frame_limit:]

    checkpoint_enabled = bool(settings["visual_turn_coarse_checkpoint_enabled"])
    checkpoint_count = int((state_payload or {}).get("checkpoint_count") or 0)
    checkpoint_interval_seconds = max(
        15,
        int(
            settings["visual_turn_first_checkpoint_interval_seconds"]
            if checkpoint_count <= 0
            else settings["visual_turn_subsequent_checkpoint_interval_seconds"]
        ),
    )
    checkpoint_min_frame_count = max(
        1,
        int(
            settings["visual_turn_first_checkpoint_min_frame_count"]
            if checkpoint_count <= 0
            else settings["visual_turn_subsequent_checkpoint_min_frame_count"]
        ),
    )
    reference_started_at = _parse_datetime(
        (state_payload or {}).get("last_checkpoint_at") or first_sample_started_at
    )
    last_checkpoint_frame_count = int((state_payload or {}).get("last_checkpoint_frame_count") or 0)
    frames_since_last_checkpoint = frame_count if checkpoint_count <= 0 else max(
        0,
        frame_count - last_checkpoint_frame_count,
    )
    sample_ended_at = _parse_datetime(frame_payload["sample_ended_at"])
    coarse_checkpoint_due = False
    next_checkpoint_due_at = None
    if checkpoint_enabled and reference_started_at is not None:
        next_checkpoint_due_at = reference_started_at + timedelta(
            seconds=checkpoint_interval_seconds
        )
        if (
            sample_ended_at is not None
            and sample_ended_at >= next_checkpoint_due_at
            and frames_since_last_checkpoint >= checkpoint_min_frame_count
        ):
            coarse_checkpoint_due = True

    return {
        "session_id": frame_payload["session_id"],
        "turn_id": frame_payload["turn_id"],
        "flow_run_id": frame_payload["flow_run_id"],
        "question_key": frame_payload["question_key"],
        "stage_id": frame_payload["stage_id"],
        "status": str((state_payload or {}).get("status") or "active"),
        "first_sample_started_at": first_sample_started_at,
        "last_sample_index": frame_payload["sample_index"],
        "frame_count": frame_count,
        "all_frame_sample_indexes": all_frame_indexes,
        "checkpoint_key_frame_sample_indexes": checkpoint_key_frame_indexes,
        "recent_frame_sample_indexes": recent_frame_indexes,
        "candidate_sample_indexes": candidate_indexes,
        "last_face_label": (frame_payload["face_result"] or {}).get("primary_label"),
        "last_pose_label": (frame_payload["pose_result"] or {}).get("primary_label"),
        "last_updated_at": frame_payload["sample_ended_at"],
        "last_checkpoint_at": (state_payload or {}).get("last_checkpoint_at"),
        "last_checkpoint_frame_count": last_checkpoint_frame_count,
        "checkpoint_count": checkpoint_count,
        "frames_since_last_checkpoint": frames_since_last_checkpoint,
        "coarse_checkpoint_due": coarse_checkpoint_due,
        "checkpoint_interval_seconds": checkpoint_interval_seconds,
        "checkpoint_min_frame_count": checkpoint_min_frame_count,
        "next_checkpoint_due_at": _isoformat(next_checkpoint_due_at),
        "finalized_at": (state_payload or {}).get("finalized_at"),
    }


def write_visual_frame_state(
    *,
    session_id: str,
    turn_id: str | None,
    flow_run_id: str,
    question_key: str,
    stage_id: str | None,
    sample_index: int,
    sample_started_at: datetime,
    sample_ended_at: datetime,
    storage_uri: str | None,
    face_result: dict[str, Any],
    pose_result: dict[str, Any],
    live_payload: dict[str, Any],
) -> VisualFrameStateWriteResult:
    try:
        client = get_optional_redis_client()
    except Exception:
        logger.warning(
            "visual redis client initialization failed session_id=%s turn_id=%s sample_index=%s",
            session_id,
            turn_id,
            sample_index,
            exc_info=True,
        )
        return VisualFrameStateWriteResult(success=False)

    if client is None:
        return VisualFrameStateWriteResult(success=False)

    settings = get_settings()
    live_key = build_visual_live_key(session_id)
    aggregate_key = build_visual_turn_aggregate_key(session_id, turn_id)
    frame_key = build_visual_turn_frame_key(session_id, turn_id, sample_index)
    state_key = build_visual_turn_state_key(session_id, turn_id)

    try:
        existing_frame_payload = _json_loads(client.get(frame_key))
        aggregate_payload = _json_loads(client.get(aggregate_key))
        state_payload = _json_loads(client.get(state_key))
        existing_live_payload = _json_loads(client.get(live_key))
        existing_candidate_payload = _json_loads(
            client.get(build_visual_turn_candidate_key(session_id, turn_id, sample_index))
        )
        if existing_frame_payload is not None:
            pipeline = client.pipeline(transaction=False)
            pipeline.expire(live_key, int(settings["visual_live_ttl_seconds"]))
            pipeline.expire(aggregate_key, int(settings["visual_turn_aggregate_ttl_seconds"]))
            pipeline.expire(frame_key, int(settings["visual_turn_frames_ttl_seconds"]))
            pipeline.expire(state_key, int(settings["visual_turn_state_ttl_seconds"]))
            if existing_candidate_payload is not None:
                pipeline.expire(
                    build_visual_turn_candidate_key(session_id, turn_id, sample_index),
                    int(settings["visual_turn_candidates_ttl_seconds"]),
                )
            pipeline.execute()
            return VisualFrameStateWriteResult(
                success=True,
                duplicate=True,
                coarse_checkpoint_due=bool((state_payload or {}).get("coarse_checkpoint_due")),
                live_payload=existing_live_payload,
                frame_payload=existing_frame_payload,
                turn_aggregate_payload=aggregate_payload,
                turn_state_payload=state_payload,
                candidate_payload=existing_candidate_payload,
            )
        frame_payload = _build_frame_payload(
            session_id=session_id,
            turn_id=turn_id,
            flow_run_id=flow_run_id,
            question_key=question_key,
            stage_id=stage_id,
            sample_index=sample_index,
            sample_started_at=sample_started_at,
            sample_ended_at=sample_ended_at,
            storage_uri=storage_uri,
            face_result=face_result,
            pose_result=pose_result,
        )
        next_live_payload = _build_live_payload(
            session_id=session_id,
            updated_at=sample_ended_at,
            live_payload=live_payload,
        )
        next_aggregate_payload = _build_turn_aggregate_payload(
            aggregate_payload=aggregate_payload,
            frame_payload=frame_payload,
        )
        candidate_payload = _build_candidate_payload(
            aggregate_payload=aggregate_payload,
            frame_payload=frame_payload,
        )
        next_state_payload = _build_turn_state_payload(
            state_payload=state_payload,
            frame_payload=frame_payload,
            candidate_payload=candidate_payload,
        )
        pruned_candidate_indexes = sorted(
            {
                int(value)
                for value in list((state_payload or {}).get("candidate_sample_indexes") or [])
                if int(value) not in set(next_state_payload["candidate_sample_indexes"])
            }
        )

        pipeline = client.pipeline(transaction=False)
        pipeline.set(
            live_key,
            _json_dumps(next_live_payload),
            ex=int(settings["visual_live_ttl_seconds"]),
        )
        pipeline.set(
            aggregate_key,
            _json_dumps(next_aggregate_payload),
            ex=int(settings["visual_turn_aggregate_ttl_seconds"]),
        )
        pipeline.set(
            frame_key,
            _json_dumps(frame_payload),
            ex=int(settings["visual_turn_frames_ttl_seconds"]),
        )
        pipeline.set(
            state_key,
            _json_dumps(next_state_payload),
            ex=int(settings["visual_turn_state_ttl_seconds"]),
        )
        if candidate_payload is not None:
            pipeline.set(
                build_visual_turn_candidate_key(session_id, turn_id, sample_index),
                _json_dumps(candidate_payload),
                ex=int(settings["visual_turn_candidates_ttl_seconds"]),
            )
        for candidate_index in pruned_candidate_indexes:
            pipeline.delete(build_visual_turn_candidate_key(session_id, turn_id, candidate_index))
        pipeline.execute()
        return VisualFrameStateWriteResult(
            success=True,
            coarse_checkpoint_due=bool(next_state_payload.get("coarse_checkpoint_due")),
            live_payload=next_live_payload,
            frame_payload=frame_payload,
            turn_aggregate_payload=next_aggregate_payload,
            turn_state_payload=next_state_payload,
            candidate_payload=candidate_payload,
        )
    except Exception:
        logger.warning(
            "visual redis write failed session_id=%s turn_id=%s sample_index=%s",
            session_id,
            turn_id,
            sample_index,
            exc_info=True,
        )
        return VisualFrameStateWriteResult(success=False)
