"""backfill new scope fields in multimodal tables

Revision ID: 20260521_0006
Revises: 20260520_0005
Create Date: 2026-05-21 10:20:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260521_0006"
down_revision = "20260520_0005"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_sessions" in existing_tables:
        session_columns = _column_names(inspector, "multimodal_sessions")
        session_assignments: list[str] = []
        if "flow_type" in session_columns:
            session_assignments.append(
                "flow_type = COALESCE(NULLIF(flow_type, ''), 'consultation')"
            )
        if "flow_run_id" in session_columns:
            flow_run_sources = ["NULLIF(flow_run_id, '')"]
            if "owner_session_id" in session_columns:
                flow_run_sources.append("NULLIF(owner_session_id, '')")
            if "consultation_session_id" in session_columns:
                flow_run_sources.append("NULLIF(consultation_session_id, '')")
            flow_run_sources.append("id")
            session_assignments.append(
                f"flow_run_id = COALESCE({', '.join(flow_run_sources)})"
            )
        if {
            "live_state_payload",
            "latest_live_payload",
        }.issubset(session_columns):
            session_assignments.append(
                "live_state_payload = COALESCE(live_state_payload, latest_live_payload)"
            )
        if session_assignments:
            op.execute(
                sa.text(
                    """
                    UPDATE multimodal_sessions
                    SET
                    """
                    + ",\n                    ".join(session_assignments)
                )
            )

    if "multimodal_captures" in existing_tables:
        capture_columns = _column_names(inspector, "multimodal_captures")
        session_columns = (
            _column_names(inspector, "multimodal_sessions")
            if "multimodal_sessions" in existing_tables
            else set()
        )
        capture_assignments: list[str] = []
        needs_session_join = False
        if {"turn_id", "consultation_turn_id"}.issubset(capture_columns):
            capture_assignments.append(
                """
                turn_id = COALESCE(
                    capture_row.turn_id,
                    capture_row.consultation_turn_id
                )
                """.strip()
            )
        if "flow_run_id" in capture_columns:
            flow_run_sources = ["NULLIF(capture_row.flow_run_id, '')"]
            if "capture_payload" in capture_columns:
                flow_run_sources.extend(
                    (
                        "NULLIF(capture_row.capture_payload ->> 'flow_run_id', '')",
                        "NULLIF(capture_row.capture_payload ->> 'consultation_session_id', '')",
                    )
                )
            if (
                "multimodal_sessions" in existing_tables
                and "session_id" in capture_columns
            ):
                if "flow_run_id" in session_columns:
                    flow_run_sources.append("NULLIF(session_row.flow_run_id, '')")
                    needs_session_join = True
                if "consultation_session_id" in session_columns:
                    flow_run_sources.append(
                        "NULLIF(session_row.consultation_session_id, '')"
                    )
                    needs_session_join = True
            capture_assignments.append(
                f"flow_run_id = COALESCE({', '.join(flow_run_sources)})"
            )
        if {
            "question_key",
            "capture_payload",
        }.issubset(capture_columns):
            capture_assignments.append(
                """
                question_key = COALESCE(
                    capture_row.question_key,
                    NULLIF(capture_row.capture_payload ->> 'question_key', '')
                )
                """.strip()
            )
        if {
            "sample_index",
            "capture_payload",
        }.issubset(capture_columns):
            capture_assignments.append(
                """
                sample_index = COALESCE(
                    capture_row.sample_index,
                    NULLIF(capture_row.capture_payload ->> 'sample_index', '')::integer,
                    NULLIF(capture_row.capture_payload ->> 'frame_index', '')::integer
                )
                """.strip()
            )
        if {
            "sample_started_at",
            "capture_payload",
        }.issubset(capture_columns):
            capture_assignments.append(
                """
                sample_started_at = COALESCE(
                    capture_row.sample_started_at,
                    NULLIF(capture_row.capture_payload ->> 'sample_started_at', '')::timestamptz,
                    NULLIF(capture_row.capture_payload ->> 'capture_started_at', '')::timestamptz
                )
                """.strip()
            )
        if {
            "sample_ended_at",
            "capture_payload",
        }.issubset(capture_columns):
            capture_assignments.append(
                """
                sample_ended_at = COALESCE(
                    capture_row.sample_ended_at,
                    NULLIF(capture_row.capture_payload ->> 'sample_ended_at', '')::timestamptz,
                    NULLIF(capture_row.capture_payload ->> 'capture_ended_at', '')::timestamptz
                )
                """.strip()
            )
        if capture_assignments:
            sql = """
                UPDATE multimodal_captures AS capture_row
                SET
            """ + ",\n                    ".join(capture_assignments)
            if (
                needs_session_join
                and "session_id" in capture_columns
                and "multimodal_sessions" in existing_tables
            ):
                sql += """
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = capture_row.session_id
                """
            op.execute(sa.text(sql))

    if "multimodal_inference_results" in existing_tables:
        result_columns = _column_names(
            inspector,
            "multimodal_inference_results",
        )
        session_columns = (
            _column_names(inspector, "multimodal_sessions")
            if "multimodal_sessions" in existing_tables
            else set()
        )
        result_assignments: list[str] = []
        needs_session_join = False
        if {"turn_id", "consultation_turn_id"}.issubset(result_columns):
            result_assignments.append(
                """
                turn_id = COALESCE(
                    result_row.turn_id,
                    result_row.consultation_turn_id
                )
                """.strip()
            )
        if "flow_run_id" in result_columns:
            flow_run_sources = ["NULLIF(result_row.flow_run_id, '')"]
            if "inference_payload" in result_columns:
                flow_run_sources.extend(
                    (
                        "NULLIF(result_row.inference_payload ->> 'flow_run_id', '')",
                        "NULLIF(result_row.inference_payload ->> 'consultation_session_id', '')",
                    )
                )
            if "flow_run_id" in session_columns:
                flow_run_sources.append("NULLIF(session_row.flow_run_id, '')")
                needs_session_join = True
            if "consultation_session_id" in session_columns:
                flow_run_sources.append(
                    "NULLIF(session_row.consultation_session_id, '')"
                )
                needs_session_join = True
            result_assignments.append(
                f"flow_run_id = COALESCE({', '.join(flow_run_sources)})"
            )
        if {
            "question_key",
            "inference_payload",
        }.issubset(result_columns):
            result_assignments.append(
                """
                question_key = COALESCE(
                    result_row.question_key,
                    NULLIF(result_row.inference_payload ->> 'question_key', '')
                )
                """.strip()
            )
        if result_assignments:
            sql = """
                UPDATE multimodal_inference_results AS result_row
                SET
            """ + ",\n                    ".join(result_assignments)
            if (
                needs_session_join
                and "session_id" in result_columns
                and "multimodal_sessions" in existing_tables
            ):
                sql += """
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = result_row.session_id
                """
            op.execute(sa.text(sql))

    if "multimodal_turn_bundles" in existing_tables:
        bundle_columns = _column_names(inspector, "multimodal_turn_bundles")
        session_columns = (
            _column_names(inspector, "multimodal_sessions")
            if "multimodal_sessions" in existing_tables
            else set()
        )
        bundle_assignments: list[str] = []
        needs_session_join = False
        if {"turn_id", "consultation_turn_id"}.issubset(bundle_columns):
            bundle_assignments.append(
                """
                turn_id = COALESCE(
                    bundle_row.turn_id,
                    bundle_row.consultation_turn_id
                )
                """.strip()
            )
        if "flow_run_id" in bundle_columns:
            flow_run_sources = ["NULLIF(bundle_row.flow_run_id, '')"]
            if "bundle_payload" in bundle_columns:
                flow_run_sources.append(
                    "NULLIF(bundle_row.bundle_payload ->> 'flow_run_id', '')"
                )
            if "flow_run_id" in session_columns:
                flow_run_sources.append("NULLIF(session_row.flow_run_id, '')")
                needs_session_join = True
            if "consultation_session_id" in session_columns:
                flow_run_sources.append(
                    "NULLIF(session_row.consultation_session_id, '')"
                )
                needs_session_join = True
            bundle_assignments.append(
                f"flow_run_id = COALESCE({', '.join(flow_run_sources)})"
            )
        if {
            "stage_id",
            "bundle_payload",
        }.issubset(bundle_columns):
            bundle_assignments.append(
                """
                stage_id = COALESCE(
                    bundle_row.stage_id,
                    NULLIF(bundle_row.bundle_payload ->> 'stage_id', '')
                )
                """.strip()
            )
        if {
            "question_key",
            "bundle_payload",
        }.issubset(bundle_columns):
            bundle_assignments.append(
                """
                question_key = COALESCE(
                    bundle_row.question_key,
                    NULLIF(bundle_row.bundle_payload ->> 'question_key', '')
                )
                """.strip()
            )
        if bundle_assignments:
            sql = """
                UPDATE multimodal_turn_bundles AS bundle_row
                SET
            """ + ",\n                    ".join(bundle_assignments)
            if (
                needs_session_join
                and "session_id" in bundle_columns
                and "multimodal_sessions" in existing_tables
            ):
                sql += """
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = bundle_row.session_id
                """
            op.execute(sa.text(sql))


def downgrade() -> None:
    pass
