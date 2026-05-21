"""add encounter scope fields to assessment sessions

Revision ID: 20260520_0004
Revises: 20260516_0003
Create Date: 2026-05-20 21:20:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520_0004"
down_revision = "20260516_0003"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "assessment_sessions" not in existing_tables:
        return

    session_columns = _column_names(inspector, "assessment_sessions")
    if "encounter_session_id" not in session_columns:
        op.add_column(
            "assessment_sessions",
            sa.Column("encounter_session_id", sa.String(length=36), nullable=True),
        )
        inspector = sa.inspect(bind)
        session_columns = _column_names(inspector, "assessment_sessions")
    if "source_consultation_flow_run_id" not in session_columns:
        op.add_column(
            "assessment_sessions",
            sa.Column(
                "source_consultation_flow_run_id",
                sa.String(length=36),
                nullable=True,
            ),
        )
        inspector = sa.inspect(bind)

    session_indexes = _index_names(inspector, "assessment_sessions")
    if "ix_assessment_sessions_encounter_session_id" not in session_indexes:
        op.create_index(
            "ix_assessment_sessions_encounter_session_id",
            "assessment_sessions",
            ["encounter_session_id"],
            unique=False,
        )
        inspector = sa.inspect(bind)
        session_indexes = _index_names(inspector, "assessment_sessions")
    if (
        "ix_assessment_sessions_source_consultation_flow_run_id"
        not in session_indexes
    ):
        op.create_index(
            "ix_assessment_sessions_source_consultation_flow_run_id",
            "assessment_sessions",
            ["source_consultation_flow_run_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "assessment_sessions" not in existing_tables:
        return

    session_columns = _column_names(inspector, "assessment_sessions")
    session_indexes = _index_names(inspector, "assessment_sessions")
    if (
        "ix_assessment_sessions_source_consultation_flow_run_id"
        in session_indexes
    ):
        op.drop_index(
            "ix_assessment_sessions_source_consultation_flow_run_id",
            table_name="assessment_sessions",
        )
    if "ix_assessment_sessions_encounter_session_id" in session_indexes:
        op.drop_index(
            "ix_assessment_sessions_encounter_session_id",
            table_name="assessment_sessions",
        )
    if "source_consultation_flow_run_id" in session_columns:
        op.drop_column(
            "assessment_sessions",
            "source_consultation_flow_run_id",
        )
    if "encounter_session_id" in session_columns:
        op.drop_column("assessment_sessions", "encounter_session_id")
