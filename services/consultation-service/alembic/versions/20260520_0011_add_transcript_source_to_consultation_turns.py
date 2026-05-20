"""add transcript_source to consultation_turns

Revision ID: 20260520_0011
Revises: 20260519_0010
Create Date: 2026-05-20 16:20:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520_0011"
down_revision = "20260519_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {
        column["name"] for column in inspector.get_columns("consultation_turns")
    }
    if "transcript_source" not in turn_columns:
        op.add_column(
            "consultation_turns",
            sa.Column("transcript_source", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {
        column["name"] for column in inspector.get_columns("consultation_turns")
    }
    if "transcript_source" in turn_columns:
        op.drop_column("consultation_turns", "transcript_source")
