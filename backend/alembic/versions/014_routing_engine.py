"""Routing policy and AIRequest routing audit fields.

Revision ID: 014
Revises: 013
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

routing_policy_type = postgresql.ENUM(
    "owner_first",
    "balanced",
    "lowest_usage",
    "cheapest",
    "priority",
    name="routing_policy_type",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE routing_policy_type AS ENUM (
                'owner_first', 'balanced', 'lowest_usage', 'cheapest', 'priority'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.add_column(
        "workspace_budget_settings",
        sa.Column(
            "routing_policy",
            routing_policy_type,
            nullable=False,
            server_default="owner_first",
        ),
    )

    op.add_column(
        "ai_requests",
        sa.Column("selected_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_requests",
        sa.Column("selected_policy", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "ai_requests",
        sa.Column("routing_policy", routing_policy_type, nullable=True),
    )
    op.add_column(
        "ai_requests",
        sa.Column("routing_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "ai_requests",
        sa.Column("routing_score", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_requests_selected_account_id",
        "ai_requests",
        "ai_accounts",
        ["selected_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ai_requests_selected_account_id",
        "ai_requests",
        ["selected_account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_requests_selected_account_id", table_name="ai_requests")
    op.drop_constraint("fk_ai_requests_selected_account_id", "ai_requests", type_="foreignkey")
    op.drop_column("ai_requests", "routing_score")
    op.drop_column("ai_requests", "routing_reason")
    op.drop_column("ai_requests", "routing_policy")
    op.drop_column("ai_requests", "selected_policy")
    op.drop_column("ai_requests", "selected_account_id")
    op.drop_column("workspace_budget_settings", "routing_policy")
    op.execute("DROP TYPE IF EXISTS routing_policy_type")
