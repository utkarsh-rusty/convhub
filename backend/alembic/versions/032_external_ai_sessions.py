"""External AI Session Foundation — migration 032.

Revision ID: 032
Revises: 031
Create Date: 2026-07-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "032"
down_revision: str | None = "031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

external_ai_provider_enum = postgresql.ENUM(
    "claude_code",
    "codex",
    "gemini_cli",
    "cursor",
    name="external_ai_provider",
    create_type=False,
)

external_ai_session_status_enum = postgresql.ENUM(
    "active",
    "closed",
    name="external_ai_session_status",
    create_type=False,
)


def upgrade() -> None:
    external_ai_provider_enum.create(op.get_bind(), checkfirst=True)
    external_ai_session_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "external_ai_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", external_ai_provider_enum, nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("machine_identifier", sa.String(length=255), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            external_ai_session_status_enum,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["repository_branch_id"], ["repository_branches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_ai_sessions_repository_id",
        "external_ai_sessions",
        ["repository_id"],
    )
    op.create_index(
        "ix_external_ai_sessions_repository_branch_id",
        "external_ai_sessions",
        ["repository_branch_id"],
    )
    op.create_index(
        "ix_external_ai_sessions_conversation_id",
        "external_ai_sessions",
        ["conversation_id"],
    )
    op.create_index(
        "ix_external_ai_sessions_workspace_user_id",
        "external_ai_sessions",
        ["workspace_user_id"],
    )
    op.create_index("ix_external_ai_sessions_status", "external_ai_sessions", ["status"])
    op.create_index("ix_external_ai_sessions_provider", "external_ai_sessions", ["provider"])

    op.create_table(
        "transcript_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_ai_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["external_ai_session_id"],
            ["external_ai_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_ai_session_id",
            "sequence_number",
            name="uq_transcript_chunks_session_sequence",
        ),
    )
    op.create_index(
        "ix_transcript_chunks_external_ai_session_id",
        "transcript_chunks",
        ["external_ai_session_id"],
    )
    op.create_index(
        "ix_transcript_chunks_session_sequence",
        "transcript_chunks",
        ["external_ai_session_id", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_chunks_session_sequence", table_name="transcript_chunks")
    op.drop_index(
        "ix_transcript_chunks_external_ai_session_id",
        table_name="transcript_chunks",
    )
    op.drop_table("transcript_chunks")

    op.drop_index("ix_external_ai_sessions_provider", table_name="external_ai_sessions")
    op.drop_index("ix_external_ai_sessions_status", table_name="external_ai_sessions")
    op.drop_index(
        "ix_external_ai_sessions_workspace_user_id",
        table_name="external_ai_sessions",
    )
    op.drop_index(
        "ix_external_ai_sessions_conversation_id",
        table_name="external_ai_sessions",
    )
    op.drop_index(
        "ix_external_ai_sessions_repository_branch_id",
        table_name="external_ai_sessions",
    )
    op.drop_index("ix_external_ai_sessions_repository_id", table_name="external_ai_sessions")
    op.drop_table("external_ai_sessions")

    external_ai_session_status_enum.drop(op.get_bind(), checkfirst=True)
    external_ai_provider_enum.drop(op.get_bind(), checkfirst=True)
