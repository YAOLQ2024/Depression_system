"""Relax legacy turn bundle column to allow Step 6 legacy-write shutdown.

Revision ID: 20260521_0007
Revises: 20260521_0006
Create Date: 2026-05-21 10:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0007"
down_revision = "20260521_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "multimodal_turn_bundles",
        "consultation_turn_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "multimodal_turn_bundles",
        "consultation_turn_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
