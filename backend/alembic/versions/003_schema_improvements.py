"""Workspace owner, message author, conversation activity, and indexes.

Revision ID: 003
Revises: 002
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_workspaces_owner_id_users",
        "workspaces",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "conversations",
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.add_column(
        "messages",
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_author_id_users",
        "messages",
        "users",
        ["author_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_workspace_members_workspace_id_user_id",
        "workspace_members",
        ["workspace_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_members_workspace_id_user_id", table_name="workspace_members")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_index("ix_conversations_project_id", table_name="conversations")

    op.drop_constraint("fk_messages_author_id_users", "messages", type_="foreignkey")
    op.drop_column("messages", "author_id")

    op.drop_column("conversations", "last_activity_at")

    op.drop_constraint("fk_workspaces_owner_id_users", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "owner_id")
