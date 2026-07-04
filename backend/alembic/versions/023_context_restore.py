"""Add restore metadata to conversations — migration 023.

Revision ID: 023
Revises: 022
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("restored_from_package_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("restored_from_commit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("restored_from_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("restored_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_restored_from_package_id",
        "conversations",
        "context_packages",
        ["restored_from_package_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_conversations_restored_from_commit_id",
        "conversations",
        "conversation_commits",
        ["restored_from_commit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_conversations_restored_from_conversation_id",
        "conversations",
        "conversations",
        ["restored_from_conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_conversations_restored_by_user_id",
        "conversations",
        "users",
        ["restored_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_restored_from_package_id",
        "conversations",
        ["restored_from_package_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_restored_from_package_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_restored_by_user_id", "conversations", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_conversations_restored_from_conversation_id",
        "conversations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conversations_restored_from_commit_id", "conversations", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_conversations_restored_from_package_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "restored_at")
    op.drop_column("conversations", "restored_by_user_id")
    op.drop_column("conversations", "restored_from_conversation_id")
    op.drop_column("conversations", "restored_from_commit_id")
    op.drop_column("conversations", "restored_from_package_id")
