"""Move conversations from projects to workspaces and add archive support.

Revision ID: 006
Revises: 005
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE conversations
        SET workspace_id = projects.workspace_id
        FROM projects
        WHERE conversations.project_id = projects.id
        """
    )

    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_constraint("conversations_project_id_fkey", "conversations", type_="foreignkey")
    op.drop_column("conversations", "project_id")

    op.alter_column("conversations", "workspace_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_workspace_id_workspaces",
        "conversations",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])

    op.execute(
        """
        UPDATE conversations
        SET title = 'Untitled Conversation'
        WHERE title IS NULL
        """
    )
    op.alter_column(
        "conversations",
        "title",
        existing_type=sa.String(length=255),
        nullable=False,
        server_default="Untitled Conversation",
    )
    op.alter_column("conversations", "title", server_default=None)


def downgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.drop_index("ix_conversations_workspace_id", table_name="conversations")
    op.drop_constraint("fk_conversations_workspace_id_workspaces", "conversations", type_="foreignkey")
    op.drop_column("conversations", "workspace_id")
    op.drop_column("conversations", "archived_at")

    op.alter_column(
        "conversations",
        "title",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.create_foreign_key(
        "conversations_project_id_fkey",
        "conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])
