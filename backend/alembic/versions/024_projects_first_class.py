"""Promote Projects to first-class containers for conversations.

Revision ID: 024
Revises: 023
Create Date: 2026-07-04

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_PROJECT_NAME = "Default Project"


def upgrade() -> None:
    op.add_column("projects", sa.Column("icon", sa.String(length=50), nullable=True))
    op.add_column("projects", sa.Column("color", sa.String(length=50), nullable=True))
    op.add_column(
        "projects",
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_projects_created_by_id",
        "projects",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_created_by_id", "projects", ["created_by_id"])

    connection = op.get_bind()
    workspaces = connection.execute(
        sa.text("SELECT id, owner_id FROM workspaces")
    ).fetchall()

    for workspace_id, owner_id in workspaces:
        existing = connection.execute(
            sa.text(
                """
                SELECT id FROM projects
                WHERE workspace_id = :workspace_id AND name = :name
                LIMIT 1
                """
            ),
            {"workspace_id": workspace_id, "name": DEFAULT_PROJECT_NAME},
        ).fetchone()

        if existing is not None:
            default_project_id = existing[0]
        else:
            default_project_id = uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO projects (
                        id, workspace_id, name, description, created_by_id,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :workspace_id, :name, :description, :created_by_id,
                        now(), now()
                    )
                    """
                ),
                {
                    "id": default_project_id,
                    "workspace_id": workspace_id,
                    "name": DEFAULT_PROJECT_NAME,
                    "description": "Default project for workspace conversations",
                    "created_by_id": owner_id,
                },
            )

        connection.execute(
            sa.text(
                """
                UPDATE conversations
                SET project_id = :project_id
                WHERE workspace_id = :workspace_id AND project_id IS NULL
                """
            ),
            {"project_id": default_project_id, "workspace_id": workspace_id},
        )

    op.alter_column(
        "conversations",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "fk_conversations_project_id_projects",
        "conversations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conversations_project_id_projects",
        "conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_project_id_projects",
        "conversations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conversations_project_id_projects",
        "conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "conversations",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_index("ix_projects_created_by_id", table_name="projects")
    op.drop_constraint("fk_projects_created_by_id", "projects", type_="foreignkey")
    op.drop_column("projects", "archived_at")
    op.drop_column("projects", "created_by_id")
    op.drop_column("projects", "color")
    op.drop_column("projects", "icon")
