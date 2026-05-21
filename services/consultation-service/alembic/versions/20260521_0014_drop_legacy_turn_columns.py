"""Drop legacy consultation turn columns after Step 7 hard cut.

Revision ID: 20260521_0014
Revises: 20260521_0013
Create Date: 2026-05-21 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0014"
down_revision = "20260521_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column_name in [
        "workflow_stage_id",
        "prompt_key",
        "prompt_order",
        "prompt_video_asset_id",
        "prompt_video_uri",
        "prompt_question_text",
        "prompt_subtitle_text",
        "multimodal_bundle_payload",
    ]:
        op.drop_column("consultation_turns", column_name)


def downgrade() -> None:
    op.add_column(
        "consultation_turns",
        sa.Column("multimodal_bundle_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_subtitle_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_question_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_video_uri", sa.Text(), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_video_asset_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_order", sa.Integer(), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "consultation_turns",
        sa.Column(
            "workflow_stage_id",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("consultation_turns", "workflow_stage_id", server_default=None)
