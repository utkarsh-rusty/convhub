"""Add conversation checkpoints and commits — migration 021.

Revision ID: 021
Revises: 020
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latest_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["latest_message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_checkpoint_id"],
            ["conversation_checkpoints.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_checkpoints_conversation_id",
        "conversation_checkpoints",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_checkpoints_latest_message_id",
        "conversation_checkpoints",
        ["latest_message_id"],
    )
    op.create_index(
        "ix_conversation_checkpoints_parent_checkpoint_id",
        "conversation_checkpoints",
        ["parent_checkpoint_id"],
    )

    op.create_table(
        "conversation_commits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commit_hash", sa.String(length=7), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latest_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_commit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"],
            ["conversation_checkpoints.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["latest_message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_commit_id"],
            ["conversation_commits.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkpoint_id"),
        sa.UniqueConstraint("commit_hash"),
    )
    op.create_index(
        "ix_conversation_commits_conversation_id",
        "conversation_commits",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_commits_commit_hash",
        "conversation_commits",
        ["commit_hash"],
        unique=True,
    )
    op.create_index(
        "ix_conversation_commits_checkpoint_id",
        "conversation_commits",
        ["checkpoint_id"],
    )
    op.create_index(
        "ix_conversation_commits_parent_commit_id",
        "conversation_commits",
        ["parent_commit_id"],
    )
    op.create_index(
        "ix_conversation_commits_created_by_id",
        "conversation_commits",
        ["created_by_id"],
    )

    # Backfill one initial checkpoint per conversation that has messages.
    op.execute(
        """
        INSERT INTO conversation_checkpoints (
            id,
            conversation_id,
            latest_message_id,
            parent_checkpoint_id,
            created_at
        )
        SELECT
            gen_random_uuid(),
            latest.conversation_id,
            latest.id,
            NULL,
            COALESCE(latest.created_at, now())
        FROM (
            SELECT DISTINCT ON (m.conversation_id)
                m.id,
                m.conversation_id,
                m.created_at
            FROM messages AS m
            ORDER BY m.conversation_id, m.created_at DESC, m.id DESC
        ) AS latest
        """
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_commits_created_by_id", table_name="conversation_commits")
    op.drop_index("ix_conversation_commits_parent_commit_id", table_name="conversation_commits")
    op.drop_index("ix_conversation_commits_checkpoint_id", table_name="conversation_commits")
    op.drop_index("ix_conversation_commits_commit_hash", table_name="conversation_commits")
    op.drop_index("ix_conversation_commits_conversation_id", table_name="conversation_commits")
    op.drop_table("conversation_commits")

    op.drop_index(
        "ix_conversation_checkpoints_parent_checkpoint_id",
        table_name="conversation_checkpoints",
    )
    op.drop_index(
        "ix_conversation_checkpoints_latest_message_id",
        table_name="conversation_checkpoints",
    )
    op.drop_index(
        "ix_conversation_checkpoints_conversation_id",
        table_name="conversation_checkpoints",
    )
    op.drop_table("conversation_checkpoints")
