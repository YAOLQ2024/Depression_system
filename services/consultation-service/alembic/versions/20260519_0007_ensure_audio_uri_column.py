"""ensure consultation_turns.audio_uri exists

Revision ID: 20260519_0007
Revises: 20260519_0006
Create Date: 2026-05-19 12:20:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260519_0007"
down_revision = "20260519_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {column["name"] for column in inspector.get_columns("consultation_turns")}
    if "audio_uri" not in turn_columns:
        op.add_column("consultation_turns", sa.Column("audio_uri", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {column["name"] for column in inspector.get_columns("consultation_turns")}
    if "audio_uri" in turn_columns:
        op.drop_column("consultation_turns", "audio_uri")
