"""Add context_packages table — migration 022.

Revision ID: 022
Revises: 021
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="generated"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("statistics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("search_keywords_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["commit_id"],
            ["conversation_commits.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commit_id"),
    )
    op.create_index(
        "ix_context_packages_conversation_id",
        "context_packages",
        ["conversation_id"],
    )
    op.create_index(
        "ix_context_packages_commit_id",
        "context_packages",
        ["commit_id"],
        unique=True,
    )
    op.alter_column("context_packages", "version", server_default=None)
    op.alter_column("context_packages", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_context_packages_commit_id", table_name="context_packages")
    op.drop_index("ix_context_packages_conversation_id", table_name="context_packages")
    op.drop_table("context_packages")
