"""Workspace budget settings and defaults.

Revision ID: 013
Revises: 012
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_budget_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "monthly_default_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("5000.00"),
        ),
        sa.Column(
            "allow_credit_borrowing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allow_emergency_pool",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allow_local_models",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_index(
        "ix_workspace_budget_settings_workspace_id",
        "workspace_budget_settings",
        ["workspace_id"],
        unique=True,
    )

    op.execute(
        """
        INSERT INTO workspace_budget_settings (
            id,
            workspace_id,
            monthly_default_credits,
            allow_credit_borrowing,
            allow_emergency_pool,
            allow_local_models,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            w.id,
            5000.00,
            false,
            false,
            true,
            now(),
            now()
        FROM workspaces w
        """
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_budget_settings_workspace_id", table_name="workspace_budget_settings")
    op.drop_table("workspace_budget_settings")
