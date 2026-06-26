"""Add default_model to ai_accounts.

Revision ID: 011
Revises: 010
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_accounts",
        sa.Column("default_model", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_accounts", "default_model")
