from __future__ import annotations

import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.clients.multimodal_client import (
    create_multimodal_session as create_upstream_multimodal_session,
    finalize_multimodal_turn as finalize_upstream_multimodal_turn,
    get_multimodal_turn_bundle as fetch_upstream_multimodal_turn_bundle,
    stream_multimodal_live as stream_upstream_multimodal_live,
    submit_visual_capture as submit_upstream_visual_capture,
)
from app.database import get_db_session
from app.models import ConsultationSession, ConsultationTurn, EncounterSession
from app.schemas.consultations import (
    ConsultationTurnRequest,
    CreateConsultationSessionRequest,
)
from app.services.consultation import (
    ConsultationServiceError,
    _ensure_json_dict,
    _now,
)
from app.services.consultation._multimodal_bridge import (
    _ensure_multimodal_session_binding,
    _extract_optional_upstream_data,
    _extract_upstream_data,
    _refresh_multimodal_live_snapshot,
)
from app.services.consultation._session_state import (
    _apply_extraction,
    _default_engine_state,
    _normalize_text,
    _resolve_current_question_item,
    _resolve_current_question_item_object,
    _resolve_current_stage_progress,
    _resolve_response_window,
    _resolve_transcript_source,
    _sync_playlist_state,
)
from app.services.consultation._subtitle_history import (
    _ensure_subtitle_history,
    _finalize_user_subtitle_entry,
)
from app.services.consultation._workflow_runtime import (
    _auto_advance,
    _clear_active_turn,
    _get_active_turn_id,
    _move_to_target,
)
from app.services.workflow_loader import WorkflowBundle, get_workflow_loader


def _infer_branch(payload: ConsultationTurnRequest) -> str:
    if payload.input_type == "silence":
        return "silence"
    if payload.input_type == "recognition_failure":
        return "recognition_failure"
    return "normal"


def _serialize_session(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> dict[str, Any]:
    engine_state = _ensure_json_dict(session_record.engine_state)
    slot_values = _ensure_json_dict(session_record.slot_values)
    current_prompt = engine_state.get("current_prompt")
    current_question_item = _resolve_current_question_item(
        session_record, bundle
    )
    current_stage_progress = _resolve_current_stage_progress(
        session_record, bundle
    )
    return {
        "session_id": session_record.id,
        "encounter_session_id": session_record.encounter_session_id,
        "user_id": session_record.user_id,
        "workflow_id": session_record.workflow_id,
        "script_bundle": session_record.script_bundle,
        "playlist_version": session_record.playlist_version
        or bundle.digital_human_playlist.playlist_version,
        "playlist_manifest_status": (
            bundle.digital_human_playlist.manifest_status
        ),
        "delivery_mode": bundle.digital_human_playlist.delivery_mode,
        "total_prompt_count": session_record.total_prompt_count,
        "completed_prompt_count": session_record.completed_prompt_count,
        "workflow_stage_id": session_record.workflow_stage_id,
        "current_stage_id": session_record.current_stage_id,
        "current_node_id": session_record.current_node_id,
        "current_question_key": session_record.current_question_key,
        "current_question_order": session_record.current_question_order,
        "current_question_video_asset_id": (
            session_record.current_question_video_asset_id
        ),
        "current_question_video_uri": (
            session_record.current_question_video_uri
        ),
        "current_question_text": session_record.current_question_text,
        "current_question_subtitle_text": (
            session_record.current_question_subtitle_text
        ),
        "current_stage": current_stage_progress,
        "status": session_record.status,
        "current_turn_id": _get_active_turn_id(session_record),
        "assigned_doctor_persona": session_record.assigned_doctor_persona,
        "requires_human_review": session_record.requires_human_review,
        "current_prompt": current_prompt,
        "current_question_item": current_question_item,
        "participant_profile_snapshot": _ensure_json_dict(
            session_record.participant_profile_snapshot
        ),
        "slot_values": slot_values,
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "chief_complaint_structured_result": (
            slot_values.get("chief_complaint_structured_result") or {}
        ),
        "chief_complaint_stage_summary": (
            slot_values.get("chief_complaint_stage_summary")
            or session_record.chief_complaint_summary
        ),
        "current_history_structured_result": (
            session_record.current_history_structured_result or {}
        ),
        "symptom_screening_stage_summary": (
            slot_values.get("symptom_screening_stage_summary") or ""
        ),
        "high_risk_screening_result": (
            session_record.high_risk_screening_result or {}
        ),
        "high_risk_screening_stage_summary": (
            slot_values.get("high_risk_screening_stage_summary") or ""
        ),
        "digital_human_consultation_summary": (
            slot_values.get("digital_human_consultation_summary") or ""
        ),
        "multimodal_session_id": session_record.multimodal_session_id,
        "multimodal_live": {},
        "multimodal_live_updated_at": None,
        "subtitle_history": _ensure_subtitle_history(
            session_record.subtitle_history_payload
        ),
        "scale_handoff_payload": session_record.scale_handoff_payload or {},
        "required_scales": bundle.required_scales,
        "created_at": session_record.created_at.isoformat(),
        "updated_at": session_record.updated_at.isoformat(),
        "started_at": session_record.started_at.isoformat()
        if session_record.started_at
        else None,
        "completed_at": session_record.completed_at.isoformat()
        if session_record.completed_at
        else None,
    }


def _get_session_or_raise(
    db_session: Session, session_id: str
) -> ConsultationSession:
    session_record = db_session.get(ConsultationSession, session_id)
    if not session_record:
        raise ConsultationServiceError(
            "consultation session not found", code=4041, status_code=404
        )
    return session_record


def _require_acting_user_id(acting_user_id: str | None) -> str:
    if not acting_user_id:
        raise ConsultationServiceError(
            "missing acting user id", code=4013, status_code=401
        )
    return acting_user_id


def _finalize_turn_bundle_upstream(
    *,
    multimodal_session_id: str | None,
    turn_id: str | None,
    acting_user_id: str,
) -> dict[str, Any] | None:
    if not multimodal_session_id or not turn_id:
        return None
    finalize_data = _extract_optional_upstream_data(
        finalize_upstream_multimodal_turn(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5025,
        allowed_statuses={404},
    )
    if not isinstance(finalize_data, dict):
        return None
    turn_bundle = finalize_data.get("turn_bundle")
    return turn_bundle if isinstance(turn_bundle, dict) else None


def create_consultation_session(
    payload: CreateConsultationSessionRequest, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    if payload.user_id != acting_user_id:
        raise ConsultationServiceError(
            "user mismatch for consultation creation",
            code=4031,
            status_code=403,
        )
    bundle = get_workflow_loader().load_bundle()
    persona_id = (
        payload.assigned_doctor_persona
        or get_workflow_loader().default_persona
    )
    if persona_id not in bundle.doctor_personas:
        raise ConsultationServiceError(
            "doctor persona not found", code=4006, status_code=404
        )

    encounter_session_id = str(uuid.uuid4())
    consultation_session_id = str(uuid.uuid4())
    multimodal_data = _extract_upstream_data(
        create_upstream_multimodal_session(
            user_id=payload.user_id,
            encounter_session_id=encounter_session_id,
            flow_type="consultation",
            flow_run_id=consultation_session_id,
        ),
        error_code=5021,
    )
    multimodal_session = multimodal_data.get("multimodal_session") or {}
    multimodal_session_id = multimodal_session.get("id")
    if not multimodal_session_id:
        raise ConsultationServiceError(
            "multimodal session id missing",
            code=5022,
            status_code=502,
        )

    first_stage_id = bundle.substeps[0]
    first_stage = bundle.stage_scripts[first_stage_id]
    now = _now()
    context_snapshot = {
        "participant_profile_snapshot_loaded": True,
        "assigned_doctor_persona_loaded": True,
        "audio_channel_ready": payload.audio_channel_ready,
        "consent_confirmed": payload.consent_confirmed,
        "participant_profile_snapshot": payload.participant_profile_snapshot,
        "assigned_doctor_persona": persona_id,
        "device_status": payload.device_status,
        "consultation_ready_state": payload.consultation_ready_state,
    }
    encounter_record = EncounterSession(
        id=encounter_session_id,
        user_id=payload.user_id,
        entry_flow_type="consultation",
        current_flow_type="consultation",
        status="draft",
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    session_record = ConsultationSession(
        id=consultation_session_id,
        encounter_session_id=encounter_session_id,
        user_id=payload.user_id,
        workflow_id=bundle.workflow_id,
        script_bundle=bundle.script_bundle,
        playlist_version=bundle.digital_human_playlist.playlist_version or None,
        workflow_stage_id=bundle.consultation_stage_id,
        current_stage_id=first_stage_id,
        current_node_id=first_stage.entry_node,
        status="draft",
        assigned_doctor_persona=persona_id,
        requires_human_review=False,
        participant_profile_snapshot=payload.participant_profile_snapshot,
        context_snapshot=context_snapshot,
        slot_values={},
        engine_state=_default_engine_state(),
        multimodal_session_id=multimodal_session_id,
        subtitle_history_payload=[],
        created_at=now,
        updated_at=now,
    )
    _sync_playlist_state(session_record, bundle)

    with get_db_session() as db_session:
        db_session.add(encounter_record)
        db_session.add(session_record)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def get_consultation_session(
    session_id: str, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        return _serialize_session(session_record, bundle)


def start_consultation_session(
    session_id: str, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        if session_record.status not in {"draft", "running"}:
            raise ConsultationServiceError(
                "consultation session cannot be started in current status",
                code=4091,
                status_code=409,
            )
        if not session_record.started_at:
            session_record.started_at = _now()
        session_record.status = "running"
        session_record.updated_at = _now()
        if session_record.encounter_session is not None:
            session_record.encounter_session.status = "in_progress"
            session_record.encounter_session.started_at = (
                session_record.encounter_session.started_at
                or session_record.started_at
            )
            session_record.encounter_session.updated_at = _now()
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def complete_system_question_item(
    session_id: str,
    question_key: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        if (
            session_record.status != "waiting_system_completion"
            or not session_record.current_stage_id
            or not session_record.current_node_id
        ):
            raise ConsultationServiceError(
                "consultation session is not waiting for system completion",
                code=4093,
                status_code=409,
            )

        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]
        current_question_item = _resolve_current_question_item_object(
            session_record, bundle
        )
        if (
            not current_question_item
            or current_question_item.question_key != question_key
        ):
            raise ConsultationServiceError(
                "system question item mismatch", code=4008, status_code=409
            )
        if current_question_item.response_required:
            raise ConsultationServiceError(
                "question item requires user response and cannot be "
                "auto-completed",
                code=4094,
                status_code=409,
            )
        if node.type != "speak_then_complete":
            raise ConsultationServiceError(
                "current node does not support system completion",
                code=4095,
                status_code=409,
            )

        session_record.status = "running"
        session_record.updated_at = _now()
        engine_state = _ensure_json_dict(session_record.engine_state)
        engine_state["last_branch_taken"] = "system_complete"
        session_record.engine_state = engine_state

        _move_to_target(session_record, node.payload.get("next"), bundle)
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def submit_consultation_turn(
    session_id: str,
    payload: ConsultationTurnRequest,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        if (
            session_record.status != "waiting_user_input"
            or not session_record.current_stage_id
            or not session_record.current_node_id
        ):
            raise ConsultationServiceError(
                "consultation session is not waiting for user input",
                code=4092,
                status_code=409,
            )

        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]
        branch_name = _infer_branch(payload)
        branch_payload = node.payload.get("branches", {}).get(branch_name)
        if not branch_payload:
            raise ConsultationServiceError(
                "consultation branch missing", code=4007
            )

        normalized_text = _normalize_text(
            payload.raw_input, payload.transcript_text, payload.input_type
        )
        transcript_source = _resolve_transcript_source(payload)
        extracted_fields = _apply_extraction(
            session_record, node, normalized_text
        )
        current_question_item = _resolve_current_question_item_object(
            session_record, bundle
        )
        turn_timestamp = _now()
        response_started_at, response_completed_at = _resolve_response_window(
            payload
        )
        active_prompt_text = _ensure_json_dict(
            session_record.engine_state
        ).get("current_prompt")
        turn_index = (
            db_session.query(ConsultationTurn)
            .filter(ConsultationTurn.session_id == session_record.id)
            .count()
            + 1
        )
        active_turn_id = _get_active_turn_id(session_record)
        requested_turn_id = (payload.turn_id or "").strip() or None
        if (
            active_turn_id
            and requested_turn_id
            and requested_turn_id != active_turn_id
        ):
            raise ConsultationServiceError(
                "consultation turn id mismatch",
                code=4096,
                status_code=409,
            )
        turn_id = requested_turn_id or active_turn_id or str(uuid.uuid4())

        consultation_turn = ConsultationTurn(
            id=turn_id,
            encounter_session_id=session_record.encounter_session_id,
            consultation_flow_run_id=session_record.id,
            session_id=session_record.id,
            stage_id=session_record.current_stage_id,
            node_id=session_record.current_node_id,
            turn_index=turn_index,
            question_key=current_question_item.question_key
            if current_question_item
            else None,
            question_order=current_question_item.order
            if current_question_item
            else None,
            question_video_asset_id=current_question_item.video_asset_id
            if current_question_item
            else None,
            question_video_uri=current_question_item.video_uri
            if current_question_item
            else None,
            question_text=current_question_item.question_text
            if current_question_item
            else active_prompt_text,
            question_subtitle_text=(
                (
                    current_question_item.subtitle_text
                    or current_question_item.question_text
                )
                if current_question_item
                else active_prompt_text
            ),
            input_type=payload.input_type,
            prompt_text=active_prompt_text,
            raw_input=payload.raw_input,
            audio_uri=payload.audio_uri,
            transcript_text=payload.transcript_text,
            transcript_source=transcript_source,
            structured_fields=extracted_fields or None,
            turn_summary_payload=None,
            branch_taken=branch_name,
            turn_window_started_at=response_started_at,
            turn_window_completed_at=response_completed_at,
            response_started_at=response_started_at,
            response_completed_at=response_completed_at,
            created_at=turn_timestamp,
        )
        db_session.add(consultation_turn)
        _finalize_user_subtitle_entry(
            session_record,
            prompt_key=current_question_item.question_key
            if current_question_item
            else session_record.current_question_key,
            transcript_text=normalized_text,
            turn_id=turn_id,
            source=transcript_source,
        )

        multimodal_session_id = (
            str(session_record.multimodal_session_id or "").strip() or None
        )
        if payload.input_type == "speech" and not multimodal_session_id:
            multimodal_session_id = _ensure_multimodal_session_binding(
                session_record,
                acting_user_id=acting_user_id,
            )

        if multimodal_session_id:
            turn_bundle_payload = _finalize_turn_bundle_upstream(
                multimodal_session_id=multimodal_session_id,
                turn_id=turn_id,
                acting_user_id=acting_user_id,
            )
            consultation_turn.turn_summary_payload = turn_bundle_payload

        _clear_active_turn(session_record)
        session_record.status = "running"
        session_record.updated_at = _now()
        engine_state = _ensure_json_dict(session_record.engine_state)
        engine_state["last_branch_taken"] = branch_name
        session_record.engine_state = engine_state

        _move_to_target(session_record, branch_payload.get("next"), bundle)
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def get_consultation_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        live_data = _refresh_multimodal_live_snapshot(
            session_record,
            acting_user_id=acting_user_id,
        )
        return live_data


def stream_consultation_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
):
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        db_session.flush()
    return stream_upstream_multimodal_live(
        multimodal_session_id=multimodal_session_id,
        acting_user_id=acting_user_id,
    )


def get_consultation_turn_multimodal_bundle(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        consultation_turn = db_session.get(ConsultationTurn, turn_id)
        if (
            not consultation_turn
            or consultation_turn.session_id != session_record.id
        ):
            raise ConsultationServiceError(
                "consultation turn not found", code=4043, status_code=404
            )
        if consultation_turn.turn_summary_payload:
            return consultation_turn.turn_summary_payload
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        bundle_data = _extract_upstream_data(
            fetch_upstream_multimodal_turn_bundle(
                multimodal_session_id=multimodal_session_id,
                turn_id=consultation_turn.id,
                acting_user_id=acting_user_id,
            ),
            error_code=5025,
        )
        consultation_turn.turn_summary_payload = bundle_data
        db_session.add(consultation_turn)
        db_session.flush()
        return bundle_data


def submit_consultation_visual_capture(
    session_id: str,
    *,
    question_key: str,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    filename: str,
    file_bytes: bytes,
    acting_user_id: str | None,
) -> dict[str, Any]:
    return _submit_consultation_frame_capture(
        session_id,
        question_key=question_key,
        turn_id=turn_id,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
        sample_index=sample_index,
        mime_type=mime_type,
        filename=filename,
        file_bytes=file_bytes,
        acting_user_id=acting_user_id,
        submit_upstream_capture=submit_upstream_visual_capture,
        error_code=5028,
    )


def _submit_consultation_frame_capture(
    session_id: str,
    *,
    question_key: str,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    filename: str,
    file_bytes: bytes,
    acting_user_id: str | None,
    submit_upstream_capture: Callable[..., dict[str, Any]],
    error_code: int,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        capture_data = _extract_upstream_data(
            submit_upstream_capture(
                multimodal_session_id=multimodal_session_id,
                flow_run_id=session_record.id,
                question_key=question_key,
                stage_id=session_record.current_stage_id,
                turn_id=turn_id,
                sample_started_at=sample_started_at,
                sample_ended_at=sample_ended_at,
                sample_index=sample_index,
                mime_type=mime_type,
                file_bytes=file_bytes,
                filename=filename,
                acting_user_id=acting_user_id,
            ),
            error_code=error_code,
        )
        if turn_id:
            consultation_turn = db_session.get(ConsultationTurn, turn_id)
            if (
                consultation_turn
                and consultation_turn.session_id == session_record.id
            ):
                consultation_turn.turn_summary_payload = (
                    capture_data.get("turn_bundle")
                )
                db_session.add(consultation_turn)
        db_session.flush()
        return capture_data
