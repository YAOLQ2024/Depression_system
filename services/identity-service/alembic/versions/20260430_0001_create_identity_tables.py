"""create identity tables

Revision ID: 20260430_0001
Revises: None
Create Date: 2026-04-30 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260430_0001"
down_revision = None
branch_labels = None
depends_on = None


def _is_datetime_type(column_type: object) -> bool:
    return isinstance(column_type, sa.DateTime)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("password_salt", sa.Text(), nullable=False),
            sa.Column("full_name", sa.Text(), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("profile_status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("height_cm", sa.Float(), nullable=True),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("marital_status", sa.Text(), nullable=True),
            sa.Column("parents_marital_status", sa.Text(), nullable=True),
            sa.Column("parents_occupation", sa.Text(), nullable=True),
            sa.Column("prior_psychiatric_visit", sa.Text(), nullable=True),
            sa.Column("family_history", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        user_columns = {column["name"]: column for column in inspector.get_columns("users")}
        if not _is_datetime_type(user_columns["created_at"]["type"]):
            op.alter_column(
                "users",
                "created_at",
                existing_type=user_columns["created_at"]["type"],
                type_=sa.DateTime(timezone=True),
                postgresql_using="created_at::timestamptz",
            )
        if not _is_datetime_type(user_columns["updated_at"]["type"]):
            op.alter_column(
                "users",
                "updated_at",
                existing_type=user_columns["updated_at"]["type"],
                type_=sa.DateTime(timezone=True),
                postgresql_using="updated_at::timestamptz",
            )

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_email" not in user_indexes:
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not inspector.has_table("sessions"):
        op.create_table(
            "sessions",
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("token"),
        )
    else:
        session_columns = {column["name"]: column for column in inspector.get_columns("sessions")}
        if not _is_datetime_type(session_columns["created_at"]["type"]):
            op.alter_column(
                "sessions",
                "created_at",
                existing_type=session_columns["created_at"]["type"],
                type_=sa.DateTime(timezone=True),
                postgresql_using="created_at::timestamptz",
            )
        if not _is_datetime_type(session_columns["expires_at"]["type"]):
            op.alter_column(
                "sessions",
                "expires_at",
                existing_type=session_columns["expires_at"]["type"],
                type_=sa.DateTime(timezone=True),
                postgresql_using="expires_at::timestamptz",
            )

    session_indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    if "ix_sessions_user_id" not in session_indexes:
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
