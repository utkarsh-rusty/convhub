"""Add owner_id to conversations — migration 020.

Revision ID: 020
Revises: 019
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE conversations
        SET owner_id = created_by_id
        WHERE created_by_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE conversations AS c
        SET owner_id = cp.user_id
        FROM conversation_participants AS cp
        WHERE c.owner_id IS NULL
          AND cp.conversation_id = c.id
          AND cp.role = 'owner'
        """
    )
    op.execute(
        """
        UPDATE conversations AS c
        SET owner_id = w.owner_id
        FROM workspaces AS w
        WHERE c.owner_id IS NULL
          AND c.workspace_id = w.id
        """
    )
    op.alter_column("conversations", "owner_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_owner_id_users",
        "conversations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_owner_id", table_name="conversations")
    op.drop_constraint("fk_conversations_owner_id_users", "conversations", type_="foreignkey")
    op.drop_column("conversations", "owner_id")
