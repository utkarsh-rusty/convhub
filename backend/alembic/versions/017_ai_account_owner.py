"""Add owner_user_id to ai_accounts — migration 017.

Revision ID: 017
Revises: 016
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_accounts",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE ai_accounts AS a
        SET owner_user_id = w.owner_id
        FROM workspaces AS w
        WHERE a.workspace_id = w.id
        """
    )
    op.alter_column("ai_accounts", "owner_user_id", nullable=False)
    op.create_foreign_key(
        "fk_ai_accounts_owner_user_id_users",
        "ai_accounts",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_ai_accounts_owner_user_id", "ai_accounts", ["owner_user_id"])
    op.create_index(
        "ix_ai_accounts_workspace_id_owner_user_id",
        "ai_accounts",
        ["workspace_id", "owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_accounts_workspace_id_owner_user_id", table_name="ai_accounts")
    op.drop_index("ix_ai_accounts_owner_user_id", table_name="ai_accounts")
    op.drop_constraint("fk_ai_accounts_owner_user_id_users", "ai_accounts", type_="foreignkey")
    op.drop_column("ai_accounts", "owner_user_id")
