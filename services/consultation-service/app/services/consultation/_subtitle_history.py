from __future__ import annotations

import re
from typing import Any

from app.models import ConsultationSession
from app.services.consultation import _ensure_json_dict, _ensure_json_list, _now
from app.services.workflow_loader import QuestionItem


def _ensure_subtitle_history(
    value: list[Any] | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(_ensure_json_list(value), start=1):
        if not isinstance(raw_entry, dict):
            continue
        speaker = str(raw_entry.get("speaker") or "").strip().lower()
        text = str(raw_entry.get("text") or "").strip()
        if speaker not in {"doctor", "user"} or not text:
            continue
        sequence = raw_entry.get("sequence")
        try:
            normalized_sequence = int(sequence)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            normalized_sequence = index
        created_at = raw_entry.get("created_at")
        updated_at = raw_entry.get("updated_at") or created_at
        entries.append(
            {
                "entry_key": str(
                    raw_entry.get("entry_key")
                    or f"{speaker}:{normalized_sequence}:"
                    f"{raw_entry.get('prompt_key') or 'entry'}"
                ),
                "speaker": speaker,
                "text": text,
                "status": str(raw_entry.get("status") or "final"),
                "source": str(raw_entry.get("source") or ""),
                "prompt_key": raw_entry.get("prompt_key"),
                "stage_id": raw_entry.get("stage_id"),
                "node_id": raw_entry.get("node_id"),
                "turn_id": raw_entry.get("turn_id"),
                "sequence": normalized_sequence,
                "created_at": str(created_at) if created_at else None,
                "updated_at": str(updated_at) if updated_at else None,
            }
        )
    entries.sort(
        key=lambda item: (
            int(item.get("sequence") or 0),
            str(item.get("created_at") or ""),
        )
    )
    return entries


def _next_subtitle_sequence(history: list[dict[str, Any]]) -> int:
    if not history:
        return 1
    return max(int(entry.get("sequence") or 0) for entry in history) + 1


def _split_subtitle_segments(text: str | None) -> list[str]:
    normalized = (text or "").strip()
    if not normalized:
        return []

    segments: list[str] = []
    for line in (
        normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ):
        compact_line = line.strip()
        if not compact_line:
            continue
        parts = re.findall(r"[^。！？!?]+[。！？!?]?", compact_line)
        cleaned_parts = [part.strip() for part in parts if part.strip()]
        if cleaned_parts:
            segments.extend(cleaned_parts)
        else:
            segments.append(compact_line)
    return segments


def _upsert_subtitle_history_entry(
    history: list[dict[str, Any]],
    *,
    entry_key: str,
    speaker: str,
    text: str,
    status: str,
    source: str,
    prompt_key: str | None,
    stage_id: str | None,
    node_id: str | None,
    turn_id: str | None = None,
) -> bool:
    normalized_text = text.strip()
    if not normalized_text:
        return False

    timestamp = _now().isoformat()
    for entry in history:
        if entry.get("entry_key") != entry_key:
            continue
        changed = False
        for key, value in {
            "speaker": speaker,
            "text": normalized_text,
            "status": status,
            "source": source,
            "prompt_key": prompt_key,
            "stage_id": stage_id,
            "node_id": node_id,
            "turn_id": turn_id,
        }.items():
            if entry.get(key) != value:
                entry[key] = value
                changed = True
        if changed:
            entry["updated_at"] = timestamp
        return changed

    history.append(
        {
            "entry_key": entry_key,
            "speaker": speaker,
            "text": normalized_text,
            "status": status,
            "source": source,
            "prompt_key": prompt_key,
            "stage_id": stage_id,
            "node_id": node_id,
            "turn_id": turn_id,
            "sequence": _next_subtitle_sequence(history),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )
    return True


def _sync_doctor_subtitle_history(
    session_record: ConsultationSession,
    question_item: QuestionItem | None,
) -> None:
    if not question_item:
        return

    prompt_text = _ensure_json_dict(session_record.engine_state).get(
        "current_prompt"
    )
    subtitle_source = (
        question_item.subtitle_text
        or prompt_text
        or question_item.question_text
        or ""
    )
    segments = _split_subtitle_segments(subtitle_source)
    if not segments:
        return

    history = _ensure_subtitle_history(session_record.subtitle_history_payload)
    changed = False
    for index, segment in enumerate(segments):
        changed = _upsert_subtitle_history_entry(
            history,
            entry_key=f"doctor:{question_item.question_key}:{index}",
            speaker="doctor",
            text=segment,
            status="final",
            source="doctor_prompt",
            prompt_key=question_item.question_key,
            stage_id=question_item.stage_id,
            node_id=question_item.node_id,
        ) or changed
    if changed:
        session_record.subtitle_history_payload = history


def _finalize_user_subtitle_entry(
    session_record: ConsultationSession,
    *,
    prompt_key: str | None,
    transcript_text: str,
    turn_id: str,
    source: str,
) -> None:
    normalized_text = transcript_text.strip()
    if not normalized_text:
        return

    resolved_prompt_key = (
        prompt_key or session_record.current_question_key or turn_id
    )
    history = _ensure_subtitle_history(session_record.subtitle_history_payload)
    changed = _upsert_subtitle_history_entry(
        history,
        entry_key=f"user:draft:{resolved_prompt_key}",
        speaker="user",
        text=normalized_text,
        status="final",
        source=source,
        prompt_key=prompt_key,
        stage_id=session_record.current_stage_id,
        node_id=session_record.current_node_id,
        turn_id=turn_id,
    )
    if changed:
        session_record.subtitle_history_payload = history
