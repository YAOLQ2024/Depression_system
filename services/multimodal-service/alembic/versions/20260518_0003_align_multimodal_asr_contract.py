"""align multimodal asr contract

Revision ID: 20260518_0003
Revises: 20260517_0002
Create Date: 2026-05-18 11:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260518_0003"
down_revision = "20260517_0002"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_map(
    inspector: sa.Inspector,
    table_name: str,
) -> dict[str, dict[str, object]]:
    return {
        column["name"]: column
        for column in inspector.get_columns(table_name)
    }


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraint_names(
    inspector: sa.Inspector,
    table_name: str,
) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_sessions" in existing_tables:
        session_columns = _column_map(inspector, "multimodal_sessions")
        for column_name, column in (
            (
                "owner_service",
                sa.Column("owner_service", sa.String(length=128), nullable=True),
            ),
            ("stage_context", sa.Column("stage_context", sa.JSON(), nullable=True)),
            (
                "started_at",
                sa.Column(
                    "started_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            ),
        ):
            if column_name not in session_columns:
                op.add_column("multimodal_sessions", column)
                inspector = sa.inspect(bind)
                session_columns = _column_map(inspector, "multimodal_sessions")

        if "owner_session_id" not in session_columns:
            op.add_column(
                "multimodal_sessions",
                sa.Column("owner_session_id", sa.String(length=128), nullable=True),
            )
            inspector = sa.inspect(bind)
            session_columns = _column_map(inspector, "multimodal_sessions")
        else:
            op.alter_column(
                "multimodal_sessions",
                "owner_session_id",
                existing_type=session_columns["owner_session_id"]["type"],
                type_=sa.String(length=128),
                existing_nullable=bool(
                    session_columns["owner_session_id"]["nullable"]
                ),
            )
            inspector = sa.inspect(bind)
            session_columns = _column_map(inspector, "multimodal_sessions")

        owner_session_sources = ["NULLIF(owner_session_id, '')"]
        if "flow_run_id" in session_columns:
            owner_session_sources.append("NULLIF(flow_run_id, '')")
        if "consultation_session_id" in session_columns:
            owner_session_sources.append("NULLIF(consultation_session_id, '')")
        owner_session_sources.append("id")
        started_at_fallback = (
            "created_at"
            if "created_at" in session_columns
            else "CURRENT_TIMESTAMP"
        )
        op.execute(
            sa.text(
                f"""
                UPDATE multimodal_sessions
                SET owner_session_id = COALESCE({", ".join(owner_session_sources)}),
                    owner_service = COALESCE(NULLIF(owner_service, ''), 'consultation-service'),
                    stage_context = COALESCE(stage_context, '{{}}'::json),
                    started_at = COALESCE(started_at, {started_at_fallback})
                WHERE owner_session_id IS NULL
                   OR owner_session_id = ''
                   OR owner_service IS NULL
                   OR owner_service = ''
                   OR stage_context IS NULL
                   OR started_at IS NULL
                """
            )
        )

        inspector = sa.inspect(bind)
        session_columns = _column_map(inspector, "multimodal_sessions")
        for column_name in ("owner_service", "stage_context", "started_at"):
            if column_name in session_columns:
                op.alter_column(
                    "multimodal_sessions",
                    column_name,
                    existing_type=session_columns[column_name]["type"],
                    nullable=False,
                )
                inspector = sa.inspect(bind)
                session_columns = _column_map(inspector, "multimodal_sessions")

        session_constraints = _unique_constraint_names(
            inspector,
            "multimodal_sessions",
        )
        if "uq_multimodal_sessions_owner" not in session_constraints:
            op.create_unique_constraint(
                "uq_multimodal_sessions_owner",
                "multimodal_sessions",
                ["owner_service", "owner_session_id"],
            )

    if "multimodal_audio_turns" in existing_tables:
        audio_columns = _column_map(inspector, "multimodal_audio_turns")
        if (
            "stored_relative_path" in audio_columns
            and "storage_object_key" not in audio_columns
        ):
            op.alter_column(
                "multimodal_audio_turns",
                "stored_relative_path",
                existing_type=audio_columns["stored_relative_path"]["type"],
                new_column_name="storage_object_key",
            )
            inspector = sa.inspect(bind)
            audio_columns = _column_map(inspector, "multimodal_audio_turns")
        elif (
            "storage_object_key" not in audio_columns
            and "stored_relative_path" not in audio_columns
        ):
            op.add_column(
                "multimodal_audio_turns",
                sa.Column("storage_object_key", sa.Text(), nullable=True),
            )
            inspector = sa.inspect(bind)
            audio_columns = _column_map(inspector, "multimodal_audio_turns")

        for column_name, column in (
            ("turn_id", sa.Column("turn_id", sa.String(length=36), nullable=True)),
            ("stage_id", sa.Column("stage_id", sa.String(length=128), nullable=True)),
            ("node_id", sa.Column("node_id", sa.String(length=128), nullable=True)),
            (
                "transcript_text",
                sa.Column("transcript_text", sa.Text(), nullable=True),
            ),
            (
                "transcript_confidence",
                sa.Column("transcript_confidence", sa.Float(), nullable=True),
            ),
            (
                "asr_provider",
                sa.Column("asr_provider", sa.String(length=64), nullable=True),
            ),
            ("error_code", sa.Column("error_code", sa.String(length=64), nullable=True)),
            ("error_message", sa.Column("error_message", sa.Text(), nullable=True)),
        ):
            if column_name not in audio_columns:
                op.add_column("multimodal_audio_turns", column)
                inspector = sa.inspect(bind)
                audio_columns = _column_map(inspector, "multimodal_audio_turns")

        op.execute(
            sa.text(
                """
                UPDATE multimodal_audio_turns
                SET storage_object_key = COALESCE(storage_object_key, audio_uri, id),
                    stage_id = COALESCE(stage_id, 'legacy'),
                    node_id = COALESCE(node_id, 'legacy'),
                    asr_provider = COALESCE(asr_provider, 'dolphin')
                WHERE storage_object_key IS NULL
                   OR stage_id IS NULL
                   OR node_id IS NULL
                   OR asr_provider IS NULL
                """
            )
        )

        inspector = sa.inspect(bind)
        audio_columns = _column_map(inspector, "multimodal_audio_turns")
        for column_name in (
            "storage_object_key",
            "stage_id",
            "node_id",
            "asr_provider",
        ):
            if column_name in audio_columns:
                op.alter_column(
                    "multimodal_audio_turns",
                    column_name,
                    existing_type=audio_columns[column_name]["type"],
                    nullable=False,
                )
                inspector = sa.inspect(bind)
                audio_columns = _column_map(inspector, "multimodal_audio_turns")

        audio_indexes = _index_names(inspector, "multimodal_audio_turns")
        if op.f("ix_multimodal_audio_turns_turn_id") not in audio_indexes:
            op.create_index(
                op.f("ix_multimodal_audio_turns_turn_id"),
                "multimodal_audio_turns",
                ["turn_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_audio_turns" in existing_tables:
        audio_columns = _column_map(inspector, "multimodal_audio_turns")
        audio_indexes = _index_names(inspector, "multimodal_audio_turns")
        if op.f("ix_multimodal_audio_turns_turn_id") in audio_indexes:
            op.drop_index(
                op.f("ix_multimodal_audio_turns_turn_id"),
                table_name="multimodal_audio_turns",
            )
        for column_name in (
            "error_message",
            "error_code",
            "asr_provider",
            "transcript_confidence",
            "transcript_text",
            "node_id",
            "stage_id",
            "turn_id",
        ):
            if column_name in audio_columns:
                op.drop_column("multimodal_audio_turns", column_name)
                inspector = sa.inspect(bind)
                audio_columns = _column_map(inspector, "multimodal_audio_turns")
        if (
            "storage_object_key" in audio_columns
            and "stored_relative_path" not in audio_columns
        ):
            op.alter_column(
                "multimodal_audio_turns",
                "storage_object_key",
                existing_type=audio_columns["storage_object_key"]["type"],
                new_column_name="stored_relative_path",
            )

    if "multimodal_sessions" in existing_tables:
        session_columns = _column_map(inspector, "multimodal_sessions")
        session_constraints = _unique_constraint_names(
            inspector,
            "multimodal_sessions",
        )
        if "uq_multimodal_sessions_owner" in session_constraints:
            op.drop_constraint(
                "uq_multimodal_sessions_owner",
                "multimodal_sessions",
                type_="unique",
            )
        for column_name in ("started_at", "stage_context", "owner_service"):
            if column_name in session_columns:
                op.drop_column("multimodal_sessions", column_name)
                inspector = sa.inspect(bind)
                session_columns = _column_map(inspector, "multimodal_sessions")
        if "owner_session_id" in session_columns:
            op.alter_column(
                "multimodal_sessions",
                "owner_session_id",
                existing_type=session_columns["owner_session_id"]["type"],
                type_=sa.String(length=36),
                existing_nullable=bool(
                    session_columns["owner_session_id"]["nullable"]
                ),
            )
