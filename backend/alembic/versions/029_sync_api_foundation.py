"""Sync API foundation — migration 029.

Revision ID: 029
Revises: 028
Create Date: 2026-07-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "branch_memories",
        sa.Column("current_sync_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "branch_memories",
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE branch_memories
            SET current_sync_version = memory_version
            """
        )
    )
    op.alter_column("branch_memories", "current_sync_version", server_default=None)


def downgrade() -> None:
    op.drop_column("branch_memories", "last_sync_at")
    op.drop_column("branch_memories", "current_sync_version")
