"""Developer workspace sessions — migration 030.

Revision ID: 030
Revises: 029
Create Date: 2026-07-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

developer_workspace_session_status_enum = postgresql.ENUM(
    "active",
    "idle",
    "disconnected",
    "closed",
    name="developer_workspace_session_status",
    create_type=False,
)


def upgrade() -> None:
    developer_workspace_session_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "developer_workspace_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            developer_workspace_session_status_enum,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("client_version", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("working_directory", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_branch_id"], ["repository_branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_developer_workspace_sessions_workspace_id",
        "developer_workspace_sessions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_developer_workspace_sessions_repository_id",
        "developer_workspace_sessions",
        ["repository_id"],
    )
    op.create_index(
        "ix_developer_workspace_sessions_repository_branch_id",
        "developer_workspace_sessions",
        ["repository_branch_id"],
    )
    op.create_index(
        "ix_developer_workspace_sessions_conversation_id",
        "developer_workspace_sessions",
        ["conversation_id"],
    )
    op.create_index(
        "ix_developer_workspace_sessions_user_id",
        "developer_workspace_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_developer_workspace_sessions_status",
        "developer_workspace_sessions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_developer_workspace_sessions_status",
        table_name="developer_workspace_sessions",
    )
    op.drop_index(
        "ix_developer_workspace_sessions_user_id",
        table_name="developer_workspace_sessions",
    )
    op.drop_index(
        "ix_developer_workspace_sessions_conversation_id",
        table_name="developer_workspace_sessions",
    )
    op.drop_index(
        "ix_developer_workspace_sessions_repository_branch_id",
        table_name="developer_workspace_sessions",
    )
    op.drop_index(
        "ix_developer_workspace_sessions_repository_id",
        table_name="developer_workspace_sessions",
    )
    op.drop_index(
        "ix_developer_workspace_sessions_workspace_id",
        table_name="developer_workspace_sessions",
    )
    op.drop_table("developer_workspace_sessions")
    developer_workspace_session_status_enum.drop(op.get_bind(), checkfirst=True)
