"""add dual audio uri columns to consultation_turns

Revision ID: 20260519_0008
Revises: 20260519_0007
Create Date: 2026-05-19 14:35:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260519_0008"
down_revision = "20260519_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {column["name"] for column in inspector.get_columns("consultation_turns")}
    if "original_audio_uri" not in turn_columns:
        op.add_column(
            "consultation_turns",
            sa.Column("original_audio_uri", sa.Text(), nullable=True),
        )
    if "normalized_wav_uri" not in turn_columns:
        op.add_column(
            "consultation_turns",
            sa.Column("normalized_wav_uri", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_turns" not in existing_tables:
        return

    turn_columns = {column["name"] for column in inspector.get_columns("consultation_turns")}
    if "normalized_wav_uri" in turn_columns:
        op.drop_column("consultation_turns", "normalized_wav_uri")
    if "original_audio_uri" in turn_columns:
        op.drop_column("consultation_turns", "original_audio_uri")
