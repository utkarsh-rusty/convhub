"""Repository metadata and coding conversation links — migration 025.

Revision ID: 025
Revises: 024
Create Date: 2026-07-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

conversation_type_enum = postgresql.ENUM(
    "general",
    "coding",
    name="conversation_type",
    create_type=False,
)
repository_provider_enum = postgresql.ENUM(
    "github",
    "gitlab",
    "bitbucket",
    "other",
    name="repository_provider",
    create_type=False,
)
repository_visibility_enum = postgresql.ENUM(
    "public",
    "private",
    "internal",
    name="repository_visibility",
    create_type=False,
)


def upgrade() -> None:
    conversation_type_enum.create(op.get_bind(), checkfirst=True)
    repository_provider_enum.create(op.get_bind(), checkfirst=True)
    repository_visibility_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", repository_provider_enum, nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repository_name", sa.String(length=255), nullable=False),
        sa.Column("remote_url", sa.String(length=2048), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("visibility", repository_visibility_enum, nullable=False, server_default="private"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_workspace_id", "repositories", ["workspace_id"])
    op.create_index("ix_repositories_project_id", "repositories", ["project_id"])
    op.create_index("ix_repositories_created_by_id", "repositories", ["created_by_id"])

    op.add_column(
        "conversations",
        sa.Column(
            "conversation_type",
            conversation_type_enum,
            nullable=False,
            server_default="general",
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_repository_id",
        "conversations",
        "repositories",
        ["repository_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_repository_id", "conversations", ["repository_id"])
    op.create_index("ix_conversations_conversation_type", "conversations", ["conversation_type"])

    op.alter_column("conversations", "conversation_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_conversations_conversation_type", table_name="conversations")
    op.drop_index("ix_conversations_repository_id", table_name="conversations")
    op.drop_constraint("fk_conversations_repository_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "repository_id")
    op.drop_column("conversations", "conversation_type")

    op.drop_index("ix_repositories_created_by_id", table_name="repositories")
    op.drop_index("ix_repositories_project_id", table_name="repositories")
    op.drop_index("ix_repositories_workspace_id", table_name="repositories")
    op.drop_table("repositories")

    repository_visibility_enum.drop(op.get_bind(), checkfirst=True)
    repository_provider_enum.drop(op.get_bind(), checkfirst=True)
    conversation_type_enum.drop(op.get_bind(), checkfirst=True)
