"""Add canonical flow_run_id to multimodal audio turns for Step 7 hard cut.

Revision ID: 20260521_0008
Revises: 20260521_0007
Create Date: 2026-05-21 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0008"
down_revision = "20260521_0007"
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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_audio_turns" not in existing_tables:
        return

    audio_columns = _column_map(inspector, "multimodal_audio_turns")
    if "flow_run_id" not in audio_columns:
        op.add_column(
            "multimodal_audio_turns",
            sa.Column("flow_run_id", sa.String(length=36), nullable=True),
        )
        inspector = sa.inspect(bind)
        audio_columns = _column_map(inspector, "multimodal_audio_turns")

    audio_indexes = _index_names(inspector, "multimodal_audio_turns")
    if op.f("ix_multimodal_audio_turns_flow_run_id") not in audio_indexes:
        op.create_index(
            op.f("ix_multimodal_audio_turns_flow_run_id"),
            "multimodal_audio_turns",
            ["flow_run_id"],
            unique=False,
        )

    if "flow_run_id" in audio_columns:
        session_columns = (
            _column_map(inspector, "multimodal_sessions")
            if "multimodal_sessions" in existing_tables
            else {}
        )
        flow_run_sources = ["NULLIF(audio_row.flow_run_id, '')"]
        if "consultation_session_id" in audio_columns:
            flow_run_sources.append("NULLIF(audio_row.consultation_session_id, '')")
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
            flow_run_sources.append("audio_row.multimodal_session_id")
        elif "multimodal_session_id" in audio_columns:
            flow_run_sources.append("audio_row.multimodal_session_id")
        else:
            flow_run_sources.append("audio_row.id")
        sql = """
            UPDATE multimodal_audio_turns AS audio_row
            SET flow_run_id = COALESCE(
        """ + ",\n                ".join(flow_run_sources) + "\n            )"
        if needs_session_join:
            sql += """
            FROM multimodal_sessions AS session_row
            WHERE session_row.id = audio_row.multimodal_session_id
            """
        op.execute(sa.text(sql))

    inspector = sa.inspect(bind)
    audio_columns = _column_map(inspector, "multimodal_audio_turns")
    if "consultation_session_id" in audio_columns:
        op.alter_column(
            "multimodal_audio_turns",
            "consultation_session_id",
            existing_type=audio_columns["consultation_session_id"]["type"],
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_audio_turns" not in existing_tables:
        return

    audio_columns = _column_map(inspector, "multimodal_audio_turns")
    if "consultation_session_id" in audio_columns:
        op.alter_column(
            "multimodal_audio_turns",
            "consultation_session_id",
            existing_type=audio_columns["consultation_session_id"]["type"],
            nullable=False,
        )
    audio_indexes = _index_names(inspector, "multimodal_audio_turns")
    if op.f("ix_multimodal_audio_turns_flow_run_id") in audio_indexes:
        op.drop_index(
            op.f("ix_multimodal_audio_turns_flow_run_id"),
            table_name="multimodal_audio_turns",
        )
    if "flow_run_id" in audio_columns:
        op.drop_column("multimodal_audio_turns", "flow_run_id")
