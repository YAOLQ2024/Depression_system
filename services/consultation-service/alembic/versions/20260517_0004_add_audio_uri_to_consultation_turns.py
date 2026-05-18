"""add audio uri to consultation turns

Revision ID: 20260517_0004
Revises: 20260516_0003
Create Date: 2026-05-17 22:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0004"
down_revision = "20260516_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consultation_turns",
        sa.Column("audio_uri", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consultation_turns", "audio_uri")
