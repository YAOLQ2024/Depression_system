"""drop redundant consultation live snapshot columns

Revision ID: 20260527_0016
Revises: 20260521_0015
Create Date: 2026-05-27 12:10:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260527_0016"
down_revision = "20260521_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }

    if "multimodal_live_updated_at" in session_columns:
        op.drop_column("consultation_sessions", "multimodal_live_updated_at")
    if "multimodal_live_payload" in session_columns:
        op.drop_column("consultation_sessions", "multimodal_live_payload")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }

    if "multimodal_live_payload" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column("multimodal_live_payload", sa.JSON(), nullable=True),
        )
    if "multimodal_live_updated_at" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column(
                "multimodal_live_updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
