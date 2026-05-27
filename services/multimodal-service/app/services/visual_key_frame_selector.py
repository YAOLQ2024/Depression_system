from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import floor
from typing import Any, Iterable

from app.config import get_settings


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_reasons(payload: dict[str, Any] | None) -> list[str]:
    normalized: list[str] = []
    for item in list((payload or {}).get("reasons") or []):
        reason = str(item or "").strip()
        if reason:
            normalized.append(reason)
    return normalized


@dataclass(slots=True)
class VisualKeyFrameSelectorInput:
    frame_payloads: list[dict[str, Any]]
    candidate_payloads: list[dict[str, Any]] = field(default_factory=list)
    turn_state_payload: dict[str, Any] | None = None
    turn_aggregate_payload: dict[str, Any] | None = None
    strategy_version: str | None = None


@dataclass(slots=True)
class SelectedVisualKeyFrame:
    sample_index: int
    sample_started_at: str | None
    sample_ended_at: str | None
    storage_uri: str | None
    selection_bucket: str
    selection_reasons: list[str]
    score: float
    face_primary_label: str | None
    pose_primary_label: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "sample_index": self.sample_index,
            "sample_started_at": self.sample_started_at,
            "sample_ended_at": self.sample_ended_at,
            "storage_uri": self.storage_uri,
            "selection_bucket": self.selection_bucket,
            "selection_reasons": list(self.selection_reasons),
            "score": self.score,
            "face_primary_label": self.face_primary_label,
            "pose_primary_label": self.pose_primary_label,
        }


@dataclass(slots=True)
class VisualKeyFrameSelectionResult:
    strategy_version: str
    frame_count: int
    target_count: int
    turn_duration_seconds: float
    base_target_count: int
    extra_time_coverage_count: int
    selected_frames: list[SelectedVisualKeyFrame]
    applied_rules: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy_version": self.strategy_version,
            "frame_count": self.frame_count,
            "target_count": self.target_count,
            "turn_duration_seconds": self.turn_duration_seconds,
            "base_target_count": self.base_target_count,
            "extra_time_coverage_count": self.extra_time_coverage_count,
            "applied_rules": list(self.applied_rules),
            "selected_frames": [frame.to_payload() for frame in self.selected_frames],
        }


@dataclass(slots=True)
class _FrameMetrics:
    sample_index: int
    frame_payload: dict[str, Any]
    candidate_payload: dict[str, Any] | None
    ended_at: datetime | None
    anomaly_score: float
    expression_change_score: float
    posture_change_score: float


def _normalize_frame_payloads(payloads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[int, dict[str, Any]] = {}
    for payload in payloads:
        sample_index = int(payload.get("sample_index") or 0)
        if sample_index <= 0:
            continue
        deduped[sample_index] = dict(payload)
    return [deduped[index] for index in sorted(deduped)]


def _resolve_target_count(
    frame_count: int,
    *,
    turn_duration_seconds: float,
) -> tuple[int, int, int]:
    settings = get_settings()
    hard_max_count = max(1, int(settings["visual_key_frame_hard_max_count"]))
    default_max_count = max(1, int(settings["visual_key_frame_default_max_count"]))
    long_turn_step_seconds = max(15, int(settings["visual_key_frame_long_turn_step_seconds"]))

    if frame_count <= 1:
        return 1, 1, 0
    if frame_count <= 3:
        return frame_count, frame_count, 0
    if frame_count <= 5:
        base_target_count = 2
    elif frame_count <= 8:
        base_target_count = 3
    elif frame_count <= 10:
        base_target_count = 4
    else:
        base_target_count = default_max_count

    extra_time_coverage_count = 0
    if turn_duration_seconds >= long_turn_step_seconds:
        extra_time_coverage_count = floor(turn_duration_seconds / long_turn_step_seconds)

    target_count = min(
        frame_count,
        hard_max_count,
        max(2, base_target_count + extra_time_coverage_count),
    )
    extra_time_coverage_count = max(0, target_count - base_target_count)
    return target_count, base_target_count, extra_time_coverage_count


def _build_frame_metrics(
    frame_payloads: list[dict[str, Any]],
    candidate_payloads: list[dict[str, Any]],
) -> list[_FrameMetrics]:
    candidate_by_sample_index = {
        int(payload.get("sample_index") or 0): dict(payload)
        for payload in candidate_payloads
        if int(payload.get("sample_index") or 0) > 0
    }
    metrics: list[_FrameMetrics] = []
    previous_face_label: str | None = None
    previous_face_score: float | None = None
    previous_pose_label: str | None = None
    previous_pose_score: float | None = None

    for frame_payload in frame_payloads:
        sample_index = int(frame_payload["sample_index"])
        candidate_payload = candidate_by_sample_index.get(sample_index)
        candidate_reasons = _normalize_reasons(candidate_payload)
        face_result = dict(frame_payload.get("face_result") or {})
        pose_result = dict(frame_payload.get("pose_result") or {})

        anomaly_score = 0.0
        if str(face_result.get("processing_status") or "").lower() == "failed":
            anomaly_score += 4.0
        if str(pose_result.get("processing_status") or "").lower() == "failed":
            anomaly_score += 4.0
        for _, value in dict(face_result.get("quality_flags") or {}).items():
            if bool(value):
                anomaly_score += 2.0
        for _, value in dict(pose_result.get("quality_flags") or {}).items():
            if bool(value):
                anomaly_score += 2.0

        face_label = str(face_result.get("primary_label") or "").strip() or None
        face_score = _as_float(face_result.get("primary_score"))
        expression_change_score = 0.0
        if previous_face_label and face_label and face_label != previous_face_label:
            expression_change_score += 10.0
        if previous_face_score is not None and face_score is not None:
            expression_change_score += abs(face_score - previous_face_score)
        if "face_label_changed" in candidate_reasons:
            expression_change_score += 2.0

        pose_label = str(pose_result.get("primary_label") or "").strip() or None
        pose_score = _as_float(pose_result.get("primary_score"))
        posture_change_score = 0.0
        if previous_pose_label and pose_label and pose_label != previous_pose_label:
            posture_change_score += 10.0
        if previous_pose_score is not None and pose_score is not None:
            posture_change_score += abs(pose_score - previous_pose_score)
        if "pose_label_changed" in candidate_reasons:
            posture_change_score += 2.0

        metrics.append(
            _FrameMetrics(
                sample_index=sample_index,
                frame_payload=frame_payload,
                candidate_payload=candidate_payload,
                ended_at=_parse_timestamp(frame_payload.get("sample_ended_at")),
                anomaly_score=anomaly_score,
                expression_change_score=expression_change_score,
                posture_change_score=posture_change_score,
            )
        )
        previous_face_label = face_label
        previous_face_score = face_score
        previous_pose_label = pose_label
        previous_pose_score = pose_score

    return metrics


def _append_selected_frame(
    selected_by_index: dict[int, SelectedVisualKeyFrame],
    metrics: _FrameMetrics,
    *,
    selection_bucket: str,
    selection_reason: str,
    score: float,
) -> None:
    existing = selected_by_index.get(metrics.sample_index)
    if existing is not None:
        if selection_reason not in existing.selection_reasons:
            existing.selection_reasons.append(selection_reason)
        existing.score = max(existing.score, score)
        if existing.selection_bucket == "uniform_fill" and selection_bucket != "uniform_fill":
            existing.selection_bucket = selection_bucket
        return

    face_result = dict(metrics.frame_payload.get("face_result") or {})
    pose_result = dict(metrics.frame_payload.get("pose_result") or {})
    selected_by_index[metrics.sample_index] = SelectedVisualKeyFrame(
        sample_index=metrics.sample_index,
        sample_started_at=metrics.frame_payload.get("sample_started_at"),
        sample_ended_at=metrics.frame_payload.get("sample_ended_at"),
        storage_uri=metrics.frame_payload.get("storage_uri"),
        selection_bucket=selection_bucket,
        selection_reasons=[selection_reason],
        score=score,
        face_primary_label=face_result.get("primary_label"),
        pose_primary_label=pose_result.get("primary_label"),
    )


def _pick_best_metric_frame(
    metrics: list[_FrameMetrics],
    *,
    selected_sample_indexes: set[int],
    metric_name: str,
) -> _FrameMetrics | None:
    candidates = [item for item in metrics if item.sample_index not in selected_sample_indexes]
    if not candidates:
        return None
    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            -float(getattr(item, metric_name)),
            -int(item.sample_index),
        ),
    )
    best = sorted_candidates[0]
    if float(getattr(best, metric_name)) <= 0:
        return None
    return best


def _pick_uniform_fill_frames(
    metrics: list[_FrameMetrics],
    *,
    selected_sample_indexes: set[int],
    needed_count: int,
) -> list[_FrameMetrics]:
    remaining = [item for item in metrics if item.sample_index not in selected_sample_indexes]
    if needed_count <= 0 or not remaining:
        return []

    timeline = [item for item in metrics if item.ended_at is not None]
    if len(timeline) >= 2:
        start_at = timeline[0].ended_at
        end_at = timeline[-1].ended_at
    else:
        start_at = remaining[0].ended_at
        end_at = remaining[-1].ended_at

    if start_at is None or end_at is None or end_at <= start_at:
        return remaining[:needed_count]

    selected_frames: list[_FrameMetrics] = []
    remaining_by_index = {item.sample_index: item for item in remaining}
    total_seconds = max(0.001, (end_at - start_at).total_seconds())
    for slot in range(1, needed_count + 1):
        target_ratio = slot / (needed_count + 1)
        target_seconds = total_seconds * target_ratio
        best = min(
            remaining_by_index.values(),
            key=lambda item: abs(
                (
                    (_parse_timestamp(item.frame_payload.get("sample_ended_at")) or end_at)
                    - start_at
                ).total_seconds()
                - target_seconds
            ),
        )
        selected_frames.append(best)
        remaining_by_index.pop(best.sample_index, None)
        if not remaining_by_index:
            break
    return selected_frames


def select_visual_key_frames(
    selector_input: VisualKeyFrameSelectorInput,
) -> VisualKeyFrameSelectionResult:
    settings = get_settings()
    strategy_version = (
        str(selector_input.strategy_version or "").strip()
        or str(settings["visual_key_frame_strategy_version"]).strip()
        or "visual-key-frame-v1"
    )
    frame_payloads = _normalize_frame_payloads(selector_input.frame_payloads)
    if not frame_payloads:
        return VisualKeyFrameSelectionResult(
            strategy_version=strategy_version,
            frame_count=0,
            target_count=0,
            turn_duration_seconds=0.0,
            base_target_count=0,
            extra_time_coverage_count=0,
            selected_frames=[],
            applied_rules=["empty_input"],
        )

    metrics = _build_frame_metrics(frame_payloads, selector_input.candidate_payloads)
    first_started_at = _parse_timestamp(frame_payloads[0].get("sample_started_at"))
    last_ended_at = _parse_timestamp(frame_payloads[-1].get("sample_ended_at"))
    if (
        first_started_at is not None
        and last_ended_at is not None
        and last_ended_at >= first_started_at
    ):
        turn_duration_seconds = round((last_ended_at - first_started_at).total_seconds(), 3)
    else:
        turn_duration_seconds = 0.0

    effective_frame_count = max(
        len(metrics),
        int((selector_input.turn_state_payload or {}).get("frame_count") or 0),
    )
    target_count, base_target_count, extra_time_coverage_count = _resolve_target_count(
        effective_frame_count,
        turn_duration_seconds=turn_duration_seconds,
    )
    selected_by_index: dict[int, SelectedVisualKeyFrame] = {}
    applied_rules: list[str] = []

    first_frame = metrics[0]
    _append_selected_frame(
        selected_by_index,
        first_frame,
        selection_bucket="anchor",
        selection_reason="first_frame",
        score=100.0,
    )
    applied_rules.append("keep_first_frame")

    if target_count > 1 and len(metrics) > 1:
        last_frame = metrics[-1]
        _append_selected_frame(
            selected_by_index,
            last_frame,
            selection_bucket="anchor",
            selection_reason="last_frame",
            score=100.0,
        )
        applied_rules.append("keep_last_frame")

    if len(metrics) <= 3:
        for item in metrics:
            _append_selected_frame(
                selected_by_index,
                item,
                selection_bucket="all_frames",
                selection_reason="short_turn_keep_all",
                score=100.0,
            )
        applied_rules.append("short_turn_keep_all")
    else:
        selection_plan = [
            ("anomaly", "anomaly_score", "keep_highest_anomaly_frame"),
            ("face_change", "expression_change_score", "keep_highest_expression_change_frame"),
            ("pose_change", "posture_change_score", "keep_highest_posture_change_frame"),
        ]
        for bucket_name, metric_name, rule_name in selection_plan:
            if len(selected_by_index) >= target_count:
                break
            best = _pick_best_metric_frame(
                metrics,
                selected_sample_indexes=set(selected_by_index),
                metric_name=metric_name,
            )
            if best is None:
                continue
            _append_selected_frame(
                selected_by_index,
                best,
                selection_bucket=bucket_name,
                selection_reason=rule_name,
                score=float(getattr(best, metric_name)),
            )
            applied_rules.append(rule_name)

    if len(selected_by_index) < target_count:
        uniform_fill_frames = _pick_uniform_fill_frames(
            metrics,
            selected_sample_indexes=set(selected_by_index),
            needed_count=target_count - len(selected_by_index),
        )
        if uniform_fill_frames:
            applied_rules.append("uniform_time_coverage_fill")
        for item in uniform_fill_frames:
            _append_selected_frame(
                selected_by_index,
                item,
                selection_bucket="uniform_fill",
                selection_reason="uniform_time_coverage_fill",
                score=1.0,
            )

    selected_frames = [selected_by_index[index] for index in sorted(selected_by_index)]
    return VisualKeyFrameSelectionResult(
        strategy_version=strategy_version,
        frame_count=effective_frame_count,
        target_count=target_count,
        turn_duration_seconds=turn_duration_seconds,
        base_target_count=base_target_count,
        extra_time_coverage_count=extra_time_coverage_count,
        selected_frames=selected_frames[:target_count],
        applied_rules=applied_rules,
    )
