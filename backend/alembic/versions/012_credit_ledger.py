"""Credit ledger and user budgets.

Revision ID: 012
Revises: 011
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

credit_transaction_type = postgresql.ENUM(
    "allocation",
    "usage",
    "borrow",
    "lend",
    "adjustment",
    name="credit_transaction_type",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE credit_transaction_type AS ENUM (
                'allocation', 'usage', 'borrow', 'lend', 'adjustment'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "user_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "monthly_credit_limit",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("5000.00"),
        ),
        sa.Column(
            "used_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "borrowed_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "lent_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "remaining_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("5000.00"),
        ),
        sa.Column("reset_date", sa.Date(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_user_budgets_workspace_user"),
    )
    op.create_index("ix_user_budgets_workspace_id", "user_budgets", ["workspace_id"])
    op.create_index("ix_user_budgets_user_id", "user_budgets", ["user_id"])

    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", credit_transaction_type, nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_transactions_workspace_id", "credit_transactions", ["workspace_id"])
    op.create_index("ix_credit_transactions_request_id", "credit_transactions", ["request_id"])
    op.create_index("ix_credit_transactions_from_user_id", "credit_transactions", ["from_user_id"])
    op.create_index("ix_credit_transactions_to_user_id", "credit_transactions", ["to_user_id"])
    op.create_index(
        "ix_credit_transactions_workspace_created_at",
        "credit_transactions",
        ["workspace_id", "created_at"],
    )

    op.execute(
        """
        INSERT INTO user_budgets (
            id,
            workspace_id,
            user_id,
            monthly_credit_limit,
            used_credits,
            borrowed_credits,
            lent_credits,
            remaining_credits,
            reset_date,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            wm.workspace_id,
            wm.user_id,
            5000.00,
            0,
            0,
            0,
            5000.00,
            (date_trunc('month', now()) + interval '1 month')::date,
            now(),
            now()
        FROM workspace_members wm
        """
    )

    op.execute(
        """
        INSERT INTO credit_transactions (
            id,
            workspace_id,
            request_id,
            from_user_id,
            to_user_id,
            transaction_type,
            amount,
            description,
            created_at
        )
        SELECT
            gen_random_uuid(),
            ub.workspace_id,
            NULL,
            NULL,
            ub.user_id,
            'allocation',
            5000.00,
            'Initial monthly credit allocation (migration backfill)',
            now()
        FROM user_budgets ub
        """
    )


def downgrade() -> None:
    op.drop_index("ix_credit_transactions_workspace_created_at", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_to_user_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_from_user_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_request_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_workspace_id", table_name="credit_transactions")
    op.drop_table("credit_transactions")

    op.drop_index("ix_user_budgets_user_id", table_name="user_budgets")
    op.drop_index("ix_user_budgets_workspace_id", table_name="user_budgets")
    op.drop_table("user_budgets")

    op.execute("DROP TYPE IF EXISTS credit_transaction_type")
