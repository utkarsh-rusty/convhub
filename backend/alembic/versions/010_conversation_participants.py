"""Create conversation_participants table.

Revision ID: 010
Revises: 009
Create Date: 2026-06-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

conversation_participant_role_enum = postgresql.ENUM(
    "owner",
    "member",
    name="conversation_participant_role",
    create_type=False,
)


def upgrade() -> None:
    conversation_participant_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversation_participants",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", conversation_participant_role_enum, nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "user_id"),
    )
    op.create_index(
        "ix_conversation_participants_conversation_id",
        "conversation_participants",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_participants_user_id",
        "conversation_participants",
        ["user_id"],
    )

    op.execute(
        """
        INSERT INTO conversation_participants (conversation_id, user_id, role, joined_at)
        SELECT id, created_by_id, 'owner', created_at
        FROM conversations
        WHERE created_by_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_participants_user_id", table_name="conversation_participants")
    op.drop_index(
        "ix_conversation_participants_conversation_id",
        table_name="conversation_participants",
    )
    op.drop_table("conversation_participants")
    conversation_participant_role_enum.drop(op.get_bind(), checkfirst=True)
