"""Branch Memory foundation — migration 027.

Revision ID: 027
Revises: 026
Create Date: 2026-07-07

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

branch_memory_sync_status_enum = postgresql.ENUM(
    "not_synced",
    "ready",
    "outdated",
    "in_progress",
    "conflict",
    name="branch_memory_sync_status",
    create_type=False,
)


def upgrade() -> None:
    branch_memory_sync_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "repository_branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_repository_branches_repository_id_name"),
    )
    op.create_index("ix_repository_branches_repository_id", "repository_branches", ["repository_id"])

    op.create_table(
        "branch_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_convhub_branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_commit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_context_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("working_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("memory_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "sync_status",
            branch_memory_sync_status_enum,
            nullable=False,
            server_default="not_synced",
        ),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
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
            ["current_commit_id"], ["conversation_commits.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["current_context_package_id"], ["context_packages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["current_conversation_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["current_convhub_branch_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["repository_branch_id"], ["repository_branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["working_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_branch_id"),
    )
    op.create_index(
        "ix_branch_memories_repository_branch_id",
        "branch_memories",
        ["repository_branch_id"],
        unique=True,
    )

    connection = op.get_bind()
    repositories = connection.execute(
        sa.text("SELECT id, default_branch FROM repositories")
    ).fetchall()
    for repository_id, default_branch in repositories:
        branch_id = uuid.uuid4()
        memory_id = uuid.uuid4()
        branch_name = (default_branch or "main").strip() or "main"
        connection.execute(
            sa.text(
                """
                INSERT INTO repository_branches (
                    id, repository_id, name, is_default, is_active, created_at, updated_at
                ) VALUES (
                    :branch_id, :repository_id, :name, true, true, now(), now()
                )
                """
            ),
            {
                "branch_id": branch_id,
                "repository_id": repository_id,
                "name": branch_name,
            },
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO branch_memories (
                    id, repository_branch_id, memory_version, sync_status, created_at, updated_at
                ) VALUES (
                    :memory_id, :branch_id, 1, 'not_synced', now(), now()
                )
                """
            ),
            {"memory_id": memory_id, "branch_id": branch_id},
        )

    op.alter_column("repository_branches", "is_default", server_default=None)
    op.alter_column("repository_branches", "is_active", server_default=None)
    op.alter_column("branch_memories", "memory_version", server_default=None)
    op.alter_column("branch_memories", "sync_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_branch_memories_repository_branch_id", table_name="branch_memories")
    op.drop_table("branch_memories")
    op.drop_index("ix_repository_branches_repository_id", table_name="repository_branches")
    op.drop_table("repository_branches")
    branch_memory_sync_status_enum.drop(op.get_bind(), checkfirst=True)
