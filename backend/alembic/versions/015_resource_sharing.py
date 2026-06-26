"""Resource sharing — lending preferences and borrow records.

Revision ID: 015
Revises: 014
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lending_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auto_share_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "monthly_share_limit",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "minimum_reserved_credits",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("500.00"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_lending_preferences_workspace_user"),
    )
    op.create_index(
        "ix_lending_preferences_workspace_id",
        "lending_preferences",
        ["workspace_id"],
    )
    op.create_index(
        "ix_lending_preferences_user_id",
        "lending_preferences",
        ["user_id"],
    )

    op.create_table(
        "borrow_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lender_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credits", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["request_id"], ["ai_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["borrower_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_borrow_records_workspace_id", "borrow_records", ["workspace_id"])
    op.create_index("ix_borrow_records_request_id", "borrow_records", ["request_id"])
    op.create_index("ix_borrow_records_borrower_user_id", "borrow_records", ["borrower_user_id"])
    op.create_index("ix_borrow_records_lender_user_id", "borrow_records", ["lender_user_id"])

    op.execute(
        """
        INSERT INTO lending_preferences (
            id,
            workspace_id,
            user_id,
            auto_share_enabled,
            monthly_share_limit,
            minimum_reserved_credits,
            priority,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            ub.workspace_id,
            ub.user_id,
            false,
            0,
            500.00,
            0,
            now(),
            now()
        FROM user_budgets ub
        """
    )


def downgrade() -> None:
    op.drop_index("ix_borrow_records_lender_user_id", table_name="borrow_records")
    op.drop_index("ix_borrow_records_borrower_user_id", table_name="borrow_records")
    op.drop_index("ix_borrow_records_request_id", table_name="borrow_records")
    op.drop_index("ix_borrow_records_workspace_id", table_name="borrow_records")
    op.drop_table("borrow_records")
    op.drop_index("ix_lending_preferences_user_id", table_name="lending_preferences")
    op.drop_index("ix_lending_preferences_workspace_id", table_name="lending_preferences")
    op.drop_table("lending_preferences")
