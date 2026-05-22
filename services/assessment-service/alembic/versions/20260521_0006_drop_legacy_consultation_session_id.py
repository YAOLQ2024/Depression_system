"""Drop legacy consultation_session_id from assessment sessions.

Revision ID: 20260521_0006
Revises: 20260521_0005
Create Date: 2026-05-21 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0006"
down_revision = "20260521_0005"
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
    if "assessment_sessions" not in _table_names(inspector):
        return

    session_columns = _column_names(inspector, "assessment_sessions")
    if "consultation_session_id" not in session_columns:
        return

    if "encounter_session_id" in session_columns:
        unresolved_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM assessment_sessions
                WHERE consultation_session_id IS NOT NULL
                  AND encounter_session_id IS NULL
                """
            )
        ).scalar_one()
        if unresolved_count:
            return

    session_indexes = _index_names(inspector, "assessment_sessions")
    index_name = op.f("ix_assessment_sessions_consultation_session_id")
    if index_name in session_indexes:
        op.drop_index(index_name, table_name="assessment_sessions")
    op.drop_column("assessment_sessions", "consultation_session_id")


def downgrade() -> None:
    op.add_column(
        "assessment_sessions",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_assessment_sessions_consultation_session_id"),
        "assessment_sessions",
        ["consultation_session_id"],
        unique=False,
    )
