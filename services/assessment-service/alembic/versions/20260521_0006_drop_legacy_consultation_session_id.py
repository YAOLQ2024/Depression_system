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


def upgrade() -> None:
    op.drop_index(
        op.f("ix_assessment_sessions_consultation_session_id"),
        table_name="assessment_sessions",
    )
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
