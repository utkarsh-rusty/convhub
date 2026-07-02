"""Add hard_budget_enforcement to workspace_budget_settings — migration 018.

Revision ID: 018
Revises: 017
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspace_budget_settings",
        sa.Column(
            "hard_budget_enforcement",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("workspace_budget_settings", "hard_budget_enforcement", server_default=None)


def downgrade() -> None:
    op.drop_column("workspace_budget_settings", "hard_budget_enforcement")
