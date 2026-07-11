"""Repository Memory Builder v1 — migration 031.

Revision ID: 031
Revises: 030
Create Date: 2026-07-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "031"
down_revision: str | None = "030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("memory_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("latest_commit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_context_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_workspace_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("markdown_content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "json_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(
            ["latest_commit_id"], ["conversation_commits.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["latest_context_package_id"], ["context_packages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["latest_workspace_session_id"],
            ["developer_workspace_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["repository_branch_id"], ["repository_branches.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_branch_id"),
    )
    op.create_index(
        "ix_repository_memories_repository_branch_id",
        "repository_memories",
        ["repository_branch_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_repository_memories_repository_branch_id",
        table_name="repository_memories",
    )
    op.drop_table("repository_memories")
