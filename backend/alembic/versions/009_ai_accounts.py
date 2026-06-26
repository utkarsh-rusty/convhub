"""Create ai_accounts table.

Revision ID: 009
Revises: 008
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("monthly_budget", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "monthly_spent",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_accounts_workspace_id", "ai_accounts", ["workspace_id"])
    op.create_index(
        "ix_ai_accounts_workspace_id_provider",
        "ai_accounts",
        ["workspace_id", "provider"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_accounts_workspace_id_provider", table_name="ai_accounts")
    op.drop_index("ix_ai_accounts_workspace_id", table_name="ai_accounts")
    op.drop_table("ai_accounts")
