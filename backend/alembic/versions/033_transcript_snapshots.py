"""Transcript Snapshot Engine — migration 033.

Revision ID: 033
Revises: 032
Create Date: 2026-07-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "033"
down_revision: str | None = "032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transcript_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_ai_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("character_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(
            ["external_ai_session_id"],
            ["external_ai_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_ai_session_id"),
    )
    op.create_index(
        "ix_transcript_snapshots_external_ai_session_id",
        "transcript_snapshots",
        ["external_ai_session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transcript_snapshots_external_ai_session_id",
        table_name="transcript_snapshots",
    )
    op.drop_table("transcript_snapshots")
