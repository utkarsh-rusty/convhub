"""Add branching columns to conversations — migration 019.

Revision ID: 019
Revises: 018
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("parent_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("branch_from_message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("branch_name", sa.String(length=255), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_parent_conversation_id",
        "conversations",
        "conversations",
        ["parent_conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_conversations_branch_from_message_id",
        "conversations",
        "messages",
        ["branch_from_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_parent_conversation_id",
        "conversations",
        ["parent_conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_parent_conversation_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_branch_from_message_id",
        "conversations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conversations_parent_conversation_id",
        "conversations",
        type_="foreignkey",
    )
    op.drop_column("conversations", "branch_name")
    op.drop_column("conversations", "branch_from_message_id")
    op.drop_column("conversations", "parent_conversation_id")
