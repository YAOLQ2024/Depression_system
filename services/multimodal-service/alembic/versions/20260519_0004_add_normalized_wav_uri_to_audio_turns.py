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


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_audio_turns" not in existing_tables:
        return

    audio_columns = _column_names(inspector, "multimodal_audio_turns")
    if "normalized_wav_uri" not in audio_columns:
        op.add_column(
            "multimodal_audio_turns",
            sa.Column("normalized_wav_uri", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_audio_turns" not in existing_tables:
        return

    audio_columns = _column_names(inspector, "multimodal_audio_turns")
    if "normalized_wav_uri" in audio_columns:
        op.drop_column("multimodal_audio_turns", "normalized_wav_uri")
