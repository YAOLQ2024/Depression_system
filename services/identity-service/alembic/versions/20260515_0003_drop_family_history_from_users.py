"""drop family_history from users

Revision ID: 20260515_0003
Revises: 20260515_0002
Create Date: 2026-05-15 00:30:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260515_0003"
down_revision = "20260515_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "family_history" in user_columns:
        op.drop_column("users", "family_history")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "family_history" not in user_columns:
        op.add_column("users", sa.Column("family_history", sa.Text(), nullable=True))
