"""backfill new scope fields in assessment sessions

Revision ID: 20260521_0005
Revises: 20260520_0004
Create Date: 2026-05-21 10:20:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260521_0005"
down_revision = "20260520_0004"
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
    if "assessment_sessions" not in existing_tables:
        return

    session_columns = _column_names(inspector, "assessment_sessions")
    if "source_consultation_flow_run_id" not in session_columns:
        return

    op.execute(
        sa.text(
            """
            UPDATE assessment_sessions
            SET source_consultation_flow_run_id = consultation_session_id
            WHERE source_consultation_flow_run_id IS NULL
              AND consultation_session_id IS NOT NULL
            """
        )
    )

    if "consultation_sessions" in existing_tables:
        consultation_columns = _column_names(inspector, "consultation_sessions")
        required_columns = {
            "encounter_session_id",
            "consultation_session_id",
        }
        if not required_columns.issubset(session_columns) or (
            "encounter_session_id" not in consultation_columns
        ):
            return

        op.execute(
            sa.text(
                """
                UPDATE assessment_sessions AS assessment_row
                SET encounter_session_id = consultation_row.encounter_session_id
                FROM consultation_sessions AS consultation_row
                WHERE assessment_row.encounter_session_id IS NULL
                  AND assessment_row.consultation_session_id IS NOT NULL
                  AND consultation_row.id = assessment_row.consultation_session_id
                """
            )
        )


def downgrade() -> None:
    pass
