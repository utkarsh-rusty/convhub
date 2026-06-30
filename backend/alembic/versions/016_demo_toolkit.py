"""Demo & Testing Toolkit — migration 016.

Revision ID: 016
Revises: 015
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pricing_profile_type = postgresql.ENUM(
    "production",
    "demo",
    "free",
    name="pricing_profile_type",
    create_type=False,
)
provider_simulation_mode = postgresql.ENUM(
    "normal",
    "timeout",
    "unauthorized",
    "rate_limit",
    "server_error",
    name="provider_simulation_mode",
    create_type=False,
)
routing_override_mode = postgresql.ENUM(
    "normal",
    "first_account",
    "second_account",
    "random",
    "specific_account",
    name="routing_override_mode",
    create_type=False,
)


def upgrade() -> None:
    pricing_profile_type.create(op.get_bind(), checkfirst=True)
    provider_simulation_mode.create(op.get_bind(), checkfirst=True)
    routing_override_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workspace_demo_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "pricing_profile",
            pricing_profile_type,
            nullable=False,
            server_default="production",
        ),
        sa.Column(
            "provider_simulation",
            provider_simulation_mode,
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "routing_override_mode",
            routing_override_mode,
            nullable=False,
            server_default="normal",
        ),
        sa.Column("routing_override_account_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["routing_override_account_id"],
            ["ai_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_index(
        "ix_workspace_demo_settings_workspace_id",
        "workspace_demo_settings",
        ["workspace_id"],
        unique=True,
    )

    op.create_table(
        "demo_event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_demo_event_logs_workspace_id", "demo_event_logs", ["workspace_id"])
    op.create_index(
        "ix_demo_event_logs_workspace_created_at",
        "demo_event_logs",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_demo_event_logs_workspace_created_at", table_name="demo_event_logs")
    op.drop_index("ix_demo_event_logs_workspace_id", table_name="demo_event_logs")
    op.drop_table("demo_event_logs")
    op.drop_index("ix_workspace_demo_settings_workspace_id", table_name="workspace_demo_settings")
    op.drop_table("workspace_demo_settings")
    routing_override_mode.drop(op.get_bind(), checkfirst=True)
    provider_simulation_mode.drop(op.get_bind(), checkfirst=True)
    pricing_profile_type.drop(op.get_bind(), checkfirst=True)
