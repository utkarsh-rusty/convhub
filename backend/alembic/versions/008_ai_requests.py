"""Create ai_requests table.

Revision ID: 008
Revises: 007
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ai_request_status_enum = postgresql.ENUM(
    "pending",
    "completed",
    "failed",
    name="ai_request_status",
    create_type=False,
)


def upgrade() -> None:
    ai_request_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assistant_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("status", ai_request_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_requests_conversation_id", "ai_requests", ["conversation_id"])
    op.create_index("ix_ai_requests_user_message_id", "ai_requests", ["user_message_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_requests_user_message_id", table_name="ai_requests")
    op.drop_index("ix_ai_requests_conversation_id", table_name="ai_requests")
    op.drop_table("ai_requests")
    ai_request_status_enum.drop(op.get_bind(), checkfirst=True)
