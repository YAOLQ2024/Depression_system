"""Drop legacy multimodal columns and constraints after Step 7 hard cut.

Revision ID: 20260521_0009
Revises: 20260521_0008
Create Date: 2026-05-21 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0009"
down_revision = "20260521_0008"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_map(
    inspector: sa.Inspector,
    table_name: str,
) -> dict[str, dict[str, object]]:
    return {
        column["name"]: column
        for column in inspector.get_columns(table_name)
    }


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraints(
    inspector: sa.Inspector,
    table_name: str,
) -> dict[str, list[str]]:
    return {
        constraint["name"]: list(constraint.get("column_names") or [])
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_turn_bundles" in existing_tables:
        bundle_columns = _column_map(inspector, "multimodal_turn_bundles")
        if {"turn_id", "consultation_turn_id"}.issubset(bundle_columns):
            op.execute(
                sa.text(
                    """
                    UPDATE multimodal_turn_bundles
                    SET turn_id = COALESCE(turn_id, consultation_turn_id)
                    WHERE turn_id IS NULL
                    """
                )
            )

        bundle_constraints = _unique_constraints(
            inspector,
            "multimodal_turn_bundles",
        )
        expected_bundle_constraint = ["session_id", "turn_id"]
        existing_bundle_constraint = bundle_constraints.get(
            "uq_multimodal_turn_bundles_session_turn"
        )
        if (
            existing_bundle_constraint
            and existing_bundle_constraint != expected_bundle_constraint
        ):
            op.drop_constraint(
                "uq_multimodal_turn_bundles_session_turn",
                "multimodal_turn_bundles",
                type_="unique",
            )
            inspector = sa.inspect(bind)
            bundle_constraints = _unique_constraints(
                inspector,
                "multimodal_turn_bundles",
            )
        if (
            bundle_constraints.get("uq_multimodal_turn_bundles_session_turn")
            != expected_bundle_constraint
            and {"session_id", "turn_id"}.issubset(bundle_columns)
        ):
            op.create_unique_constraint(
                "uq_multimodal_turn_bundles_session_turn",
                "multimodal_turn_bundles",
                ["session_id", "turn_id"],
            )
        if "turn_id" in bundle_columns:
            op.alter_column(
                "multimodal_turn_bundles",
                "turn_id",
                existing_type=bundle_columns["turn_id"]["type"],
                nullable=False,
            )
        bundle_indexes = _index_names(inspector, "multimodal_turn_bundles")
        if op.f("ix_multimodal_turn_bundles_consultation_turn_id") in bundle_indexes:
            op.drop_index(
                op.f("ix_multimodal_turn_bundles_consultation_turn_id"),
                table_name="multimodal_turn_bundles",
            )
        if "consultation_turn_id" in bundle_columns:
            op.drop_column("multimodal_turn_bundles", "consultation_turn_id")
            inspector = sa.inspect(bind)

    if "multimodal_captures" in existing_tables:
        capture_columns = _column_map(inspector, "multimodal_captures")
        capture_indexes = _index_names(inspector, "multimodal_captures")
        if op.f("ix_multimodal_captures_consultation_turn_id") in capture_indexes:
            op.drop_index(
                op.f("ix_multimodal_captures_consultation_turn_id"),
                table_name="multimodal_captures",
            )
        if "consultation_turn_id" in capture_columns:
            op.drop_column("multimodal_captures", "consultation_turn_id")
            inspector = sa.inspect(bind)

    if "multimodal_inference_results" in existing_tables:
        result_columns = _column_map(inspector, "multimodal_inference_results")
        result_indexes = _index_names(inspector, "multimodal_inference_results")
        if (
            op.f("ix_multimodal_inference_results_consultation_turn_id")
            in result_indexes
        ):
            op.drop_index(
                op.f("ix_multimodal_inference_results_consultation_turn_id"),
                table_name="multimodal_inference_results",
            )
        if "consultation_turn_id" in result_columns:
            op.drop_column("multimodal_inference_results", "consultation_turn_id")
            inspector = sa.inspect(bind)

    if "multimodal_audio_turns" in existing_tables:
        audio_columns = _column_map(inspector, "multimodal_audio_turns")
        session_columns = (
            _column_map(inspector, "multimodal_sessions")
            if "multimodal_sessions" in existing_tables
            else {}
        )
        if "flow_run_id" in audio_columns:
            flow_run_sources = ["NULLIF(audio_row.flow_run_id, '')"]
            needs_session_join = False
            if "multimodal_session_id" in audio_columns and session_columns:
                if "flow_run_id" in session_columns:
                    flow_run_sources.append("NULLIF(session_row.flow_run_id, '')")
                    needs_session_join = True
                if "consultation_session_id" in session_columns:
                    flow_run_sources.append(
                        "NULLIF(session_row.consultation_session_id, '')"
                    )
                    needs_session_join = True
            if "consultation_session_id" in audio_columns:
                flow_run_sources.append(
                    "NULLIF(audio_row.consultation_session_id, '')"
                )
            if "multimodal_session_id" in audio_columns:
                flow_run_sources.append("audio_row.multimodal_session_id")
            flow_run_sources.append("audio_row.id")
            sql = """
                UPDATE multimodal_audio_turns AS audio_row
                SET flow_run_id = COALESCE(
            """ + ",\n                    ".join(flow_run_sources) + "\n                )"
            if needs_session_join and "multimodal_session_id" in audio_columns:
                sql += """
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = audio_row.multimodal_session_id
                """
            op.execute(sa.text(sql))

        audio_indexes = _index_names(inspector, "multimodal_audio_turns")
        if op.f("ix_multimodal_audio_turns_consultation_session_id") in audio_indexes:
            op.drop_index(
                op.f("ix_multimodal_audio_turns_consultation_session_id"),
                table_name="multimodal_audio_turns",
            )
        if "consultation_session_id" in audio_columns:
            op.drop_column("multimodal_audio_turns", "consultation_session_id")
            inspector = sa.inspect(bind)
            audio_columns = _column_map(inspector, "multimodal_audio_turns")
        if "prompt_key" in audio_columns:
            op.drop_column("multimodal_audio_turns", "prompt_key")
            inspector = sa.inspect(bind)
            audio_columns = _column_map(inspector, "multimodal_audio_turns")
        if "flow_run_id" in audio_columns:
            op.alter_column(
                "multimodal_audio_turns",
                "flow_run_id",
                existing_type=audio_columns["flow_run_id"]["type"],
                nullable=False,
            )

    if "multimodal_sessions" in existing_tables:
        session_columns = _column_map(inspector, "multimodal_sessions")
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
        if "stage_context" in session_columns:
            session_assignments.append(
                "stage_context = COALESCE(stage_context, '{}'::json)"
            )
        if "started_at" in session_columns:
            if "created_at" in session_columns:
                session_assignments.append(
                    "started_at = COALESCE(started_at, created_at)"
                )
            elif "updated_at" in session_columns:
                session_assignments.append(
                    "started_at = COALESCE(started_at, updated_at)"
                )
            else:
                session_assignments.append(
                    "started_at = COALESCE(started_at, CURRENT_TIMESTAMP)"
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

        session_constraints = _unique_constraints(
            inspector,
            "multimodal_sessions",
        )
        if "uq_multimodal_sessions_owner" in session_constraints:
            op.drop_constraint(
                "uq_multimodal_sessions_owner",
                "multimodal_sessions",
                type_="unique",
            )
            inspector = sa.inspect(bind)
            session_constraints = _unique_constraints(
                inspector,
                "multimodal_sessions",
            )
        expected_flow_scope = ["flow_type", "flow_run_id"]
        existing_flow_scope = session_constraints.get(
            "uq_multimodal_sessions_flow_scope"
        )
        if existing_flow_scope and existing_flow_scope != expected_flow_scope:
            op.drop_constraint(
                "uq_multimodal_sessions_flow_scope",
                "multimodal_sessions",
                type_="unique",
            )
            inspector = sa.inspect(bind)
            session_constraints = _unique_constraints(
                inspector,
                "multimodal_sessions",
            )
        if (
            session_constraints.get("uq_multimodal_sessions_flow_scope")
            != expected_flow_scope
            and {"flow_type", "flow_run_id"}.issubset(session_columns)
        ):
            op.create_unique_constraint(
                "uq_multimodal_sessions_flow_scope",
                "multimodal_sessions",
                ["flow_type", "flow_run_id"],
            )

        if "flow_type" in session_columns:
            op.alter_column(
                "multimodal_sessions",
                "flow_type",
                existing_type=session_columns["flow_type"]["type"],
                nullable=False,
            )
            inspector = sa.inspect(bind)
            session_columns = _column_map(inspector, "multimodal_sessions")
        if "flow_run_id" in session_columns:
            op.alter_column(
                "multimodal_sessions",
                "flow_run_id",
                existing_type=session_columns["flow_run_id"]["type"],
                nullable=False,
            )
            inspector = sa.inspect(bind)
            session_columns = _column_map(inspector, "multimodal_sessions")

        session_indexes = _index_names(inspector, "multimodal_sessions")
        if op.f("ix_multimodal_sessions_owner_session_id") in session_indexes:
            op.drop_index(
                op.f("ix_multimodal_sessions_owner_session_id"),
                table_name="multimodal_sessions",
            )
        for column_name in (
            "owner_service",
            "owner_session_id",
            "consultation_session_id",
            "latest_live_payload",
            "session_summary_payload",
        ):
            if column_name in session_columns:
                op.drop_column("multimodal_sessions", column_name)
                inspector = sa.inspect(bind)
                session_columns = _column_map(inspector, "multimodal_sessions")


def downgrade() -> None:
    op.add_column(
        "multimodal_sessions",
        sa.Column("session_summary_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("latest_live_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("owner_session_id", sa.String(length=128), nullable=False, server_default=""),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("owner_service", sa.String(length=128), nullable=False, server_default="consultation-service"),
    )
    op.create_index(
        op.f("ix_multimodal_sessions_owner_session_id"),
        "multimodal_sessions",
        ["owner_session_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_multimodal_sessions_flow_scope",
        "multimodal_sessions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        ["owner_service", "owner_session_id"],
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_type",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.alter_column("multimodal_sessions", "owner_service", server_default=None)
    op.alter_column("multimodal_sessions", "owner_session_id", server_default=None)

    op.alter_column(
        "multimodal_audio_turns",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        "multimodal_audio_turns",
        ["consultation_session_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_inference_results",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_inference_results_consultation_turn_id"),
        "multimodal_inference_results",
        ["consultation_turn_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_captures",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_captures_consultation_turn_id"),
        "multimodal_captures",
        ["consultation_turn_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_turn_bundles",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_turn_bundles_consultation_turn_id"),
        "multimodal_turn_bundles",
        ["consultation_turn_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        ["session_id", "consultation_turn_id"],
    )
    op.alter_column(
        "multimodal_turn_bundles",
        "turn_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
