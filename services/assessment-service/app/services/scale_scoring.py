from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from app.services.scale_loader import ScaleDefinition


class ScaleScoringError(Exception):
    pass


class ScoreAnswerLike(Protocol):
    item_id: str
    score_value: int


@dataclass(frozen=True)
class ScaleScoringOutcome:
    raw_score: int
    derived_score: int
    interpretation_level: str | None
    interpretation_label: str | None
    normalized_score: float | None
    risk_flags: list[dict[str, Any]]
    score_details: dict[str, Any]


def _round_score(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _clamp_score(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return value


def _score_scale(scale_definition: ScaleDefinition, answers: Sequence[ScoreAnswerLike]) -> tuple[int, int]:
    score_method = scale_definition.scoring.get("method")
    raw_score = sum(answer.score_value for answer in answers)

    if score_method == "sum":
        return raw_score, raw_score

    if score_method == "standard_score":
        reverse_items = set(scale_definition.scoring.get("reverse_scored_items") or [])
        option_scores = [option.score for option in scale_definition.answer_options]
        minimum_score = min(option_scores)
        maximum_score = max(option_scores)
        normalized_scores: list[int] = []
        for answer in answers:
            if answer.item_id in reverse_items:
                normalized_scores.append(maximum_score + minimum_score - answer.score_value)
            else:
                normalized_scores.append(answer.score_value)
        raw_score = sum(normalized_scores)
        return raw_score, int(raw_score * 1.25)

    if score_method == "sum_excluding_not_applicable":
        na_value = int(scale_definition.scoring.get("na_value", 9))
        filtered_scores = [answer.score_value for answer in answers if answer.score_value != na_value]
        raw_score = sum(filtered_scores)
        return raw_score, raw_score

    raise ScaleScoringError(f"unsupported scoring method: {score_method}")


def _resolve_interpretation(
    scale_definition: ScaleDefinition,
    derived_score: int,
) -> tuple[str | None, str | None]:
    for rule in scale_definition.scoring.get("severity_rules") or []:
        minimum = int(rule["min"])
        maximum = int(rule["max"])
        if minimum <= derived_score <= maximum:
            return str(rule.get("level")), str(rule.get("label"))
    return None, None


def _build_risk_flags(
    scale_definition: ScaleDefinition,
    answers: Sequence[ScoreAnswerLike],
) -> list[dict[str, Any]]:
    answers_by_item = {answer.item_id: answer for answer in answers}
    flags: list[dict[str, Any]] = []
    for flag_definition in scale_definition.risk_flags:
        item_id = str(flag_definition.get("item_id") or "")
        answer = answers_by_item.get(item_id)
        if not answer:
            continue
        minimum_score = int(flag_definition.get("min_score", 0))
        if answer.score_value >= minimum_score:
            flags.append(
                {
                    "flag": flag_definition.get("flag"),
                    "label": flag_definition.get("label"),
                    "item_id": answer.item_id,
                    "score_value": answer.score_value,
                }
            )
    return flags


def build_normalized_score(
    scale_definition: ScaleDefinition,
    answers: Sequence[ScoreAnswerLike],
    *,
    raw_score: int,
    derived_score: int,
) -> float | None:
    normalized_output = dict(scale_definition.scoring.get("normalized_output") or {})
    if not normalized_output:
        score_range = scale_definition.scoring.get("score_range")
        if scale_definition.scoring.get("method") == "sum" and score_range:
            normalized_output = {
                "method": "linear",
                "source_score": "derived_score",
                "minimum": int(score_range[0]),
                "maximum": int(score_range[1]),
            }
        else:
            return None

    normalized_method = str(normalized_output.get("method") or "").strip()
    if normalized_method == "linear":
        source_score_key = str(normalized_output.get("source_score") or "derived_score")
        source_score_value = derived_score if source_score_key == "derived_score" else raw_score
        minimum = float(normalized_output["minimum"])
        maximum = float(normalized_output["maximum"])
        if maximum <= minimum:
            raise ScaleScoringError(
                f"invalid normalization bounds for scale {scale_definition.slug}"
            )
        normalized_score = (float(source_score_value) - minimum) / (maximum - minimum) * 100.0
        return _round_score(_clamp_score(normalized_score))

    if normalized_method == "effective_item_ratio":
        na_value = int(normalized_output.get("na_value", scale_definition.scoring.get("na_value", 9)))
        max_score_per_applicable_item = float(normalized_output.get("max_score_per_applicable_item", 2))
        applicable_answers = [answer for answer in answers if answer.score_value != na_value]
        max_possible_score = len(applicable_answers) * max_score_per_applicable_item
        if max_possible_score <= 0:
            return None
        normalized_score = float(raw_score) / max_possible_score * 100.0
        return _round_score(_clamp_score(normalized_score))

    raise ScaleScoringError(
        f"unsupported normalization method '{normalized_method}' for scale {scale_definition.slug}"
    )


def build_score_details(
    scale_definition: ScaleDefinition,
    answers: Sequence[ScoreAnswerLike],
    *,
    raw_score: int,
    derived_score: int,
    normalized_score: float | None,
) -> dict[str, Any]:
    score_method = str(scale_definition.scoring.get("method") or "")
    reverse_scored_items = list(scale_definition.scoring.get("reverse_scored_items") or [])
    verification_status = str(scale_definition.scoring.get("verification_status") or "verified")
    details: dict[str, Any] = {
        "score_method": score_method,
        "normalized_score": normalized_score,
        "verification_status": verification_status,
        "answer_summary": {
            "configured_item_count": len(scale_definition.items),
            "answered_item_count": len(answers),
        },
    }

    normalized_output = dict(scale_definition.scoring.get("normalized_output") or {})
    if normalized_output:
        normalization_method = str(normalized_output.get("method") or "")
        source_score_key = str(normalized_output.get("source_score") or "derived_score")
        source_score_value = derived_score if source_score_key == "derived_score" else raw_score
        normalization_payload: dict[str, Any] = {
            "method": normalization_method,
            "source_score": source_score_key,
            "source_score_value": source_score_value,
        }
        if normalization_method == "linear":
            normalization_payload["minimum"] = normalized_output.get("minimum")
            normalization_payload["maximum"] = normalized_output.get("maximum")
        elif normalization_method == "effective_item_ratio":
            na_value = int(normalized_output.get("na_value", scale_definition.scoring.get("na_value", 9)))
            max_score_per_item = float(normalized_output.get("max_score_per_applicable_item", 2))
            applicable_answers = [answer for answer in answers if answer.score_value != na_value]
            excluded_items = [answer.item_id for answer in answers if answer.score_value == na_value]
            normalization_payload["na_value"] = na_value
            normalization_payload["max_score_per_applicable_item"] = max_score_per_item
            normalization_payload["applicable_item_count"] = len(applicable_answers)
            normalization_payload["excluded_not_applicable_item_ids"] = excluded_items
            normalization_payload["max_possible_score"] = _round_score(
                len(applicable_answers) * max_score_per_item
            )
        details["normalization"] = normalization_payload

    if score_method == "standard_score":
        details["standard_score_multiplier"] = 1.25
        details["reverse_scored_items"] = reverse_scored_items
        details["reverse_scored_item_count"] = len(reverse_scored_items)
        details["reverse_scored_items_applied"] = [
            answer.item_id for answer in answers if answer.item_id in set(reverse_scored_items)
        ]
    elif score_method == "sum_excluding_not_applicable":
        na_value = int(scale_definition.scoring.get("na_value", 9))
        details["not_applicable_value"] = na_value
        details["effective_item_count"] = len([answer for answer in answers if answer.score_value != na_value])

    if verification_status != "verified":
        details["scoring_warnings"] = [str(note) for note in scale_definition.notes]

    return details


def compute_scale_scoring(
    scale_definition: ScaleDefinition,
    answers: Sequence[ScoreAnswerLike],
) -> ScaleScoringOutcome:
    raw_score, derived_score = _score_scale(scale_definition, answers)
    interpretation_level, interpretation_label = _resolve_interpretation(scale_definition, derived_score)
    normalized_score = build_normalized_score(
        scale_definition,
        answers,
        raw_score=raw_score,
        derived_score=derived_score,
    )
    risk_flags = _build_risk_flags(scale_definition, answers)
    score_details = build_score_details(
        scale_definition,
        answers,
        raw_score=raw_score,
        derived_score=derived_score,
        normalized_score=normalized_score,
    )
    return ScaleScoringOutcome(
        raw_score=raw_score,
        derived_score=derived_score,
        interpretation_level=interpretation_level,
        interpretation_label=interpretation_label,
        normalized_score=normalized_score,
        risk_flags=risk_flags,
        score_details=score_details,
    )
