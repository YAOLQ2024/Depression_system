"""add normalized wav uri to multimodal audio turns

Revision ID: 20260519_0004
Revises: 20260518_0003
Create Date: 2026-05-19 23:55:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_0004"
down_revision = "20260518_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("normalized_wav_uri", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("multimodal_audio_turns", "normalized_wav_uri")
