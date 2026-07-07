"""Replace conversation_type with coding_enabled — migration 026.

Revision ID: 026
Revises: 025
Create Date: 2026-07-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: str | None = "025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("coding_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        sa.text(
            "UPDATE conversations SET coding_enabled = true WHERE conversation_type = 'coding'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE conversations SET coding_enabled = false WHERE conversation_type = 'general'"
        )
    )
    op.drop_index("ix_conversations_conversation_type", table_name="conversations")
    op.drop_column("conversations", "conversation_type")
    op.execute(sa.text("DROP TYPE IF EXISTS conversation_type"))
    op.create_index("ix_conversations_coding_enabled", "conversations", ["coding_enabled"])
    op.alter_column("conversations", "coding_enabled", server_default=None)


def downgrade() -> None:
    conversation_type_enum = sa.Enum("general", "coding", name="conversation_type")
    conversation_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "conversations",
        sa.Column(
            "conversation_type",
            conversation_type_enum,
            nullable=False,
            server_default="general",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE conversations SET conversation_type = 'coding' WHERE coding_enabled = true"
        )
    )
    op.execute(
        sa.text(
            "UPDATE conversations SET conversation_type = 'general' WHERE coding_enabled = false"
        )
    )
    op.drop_index("ix_conversations_coding_enabled", table_name="conversations")
    op.drop_column("conversations", "coding_enabled")
    op.create_index("ix_conversations_conversation_type", "conversations", ["conversation_type"])
    op.alter_column("conversations", "conversation_type", server_default=None)
