"""Branch Sync History — migration 028.

Revision ID: 028
Revises: 027
Create Date: 2026-07-07

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

branch_sync_type_enum = postgresql.ENUM(
    "local_commit",
    "restore",
    "attach_repository",
    "detach_repository",
    "plugin_push",
    "plugin_pull",
    "manual_update",
    name="branch_sync_type",
    create_type=False,
)


def upgrade() -> None:
    branch_sync_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "branch_sync_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("convhub_branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("commit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sync_type", branch_sync_type_enum, nullable=False),
        sa.Column("sync_version", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["branch_memory_id"], ["branch_memories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["commit_id"], ["conversation_commits.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["context_package_id"], ["context_packages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["convhub_branch_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "branch_memory_id",
            "sync_version",
            name="uq_branch_sync_records_branch_memory_id_sync_version",
        ),
    )
    op.create_index(
        "ix_branch_sync_records_branch_memory_id",
        "branch_sync_records",
        ["branch_memory_id"],
    )
    op.create_index(
        "ix_branch_sync_records_branch_memory_id_sync_version",
        "branch_sync_records",
        ["branch_memory_id", "sync_version"],
        unique=True,
    )

    op.add_column(
        "branch_memories",
        sa.Column("latest_sync_record_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    connection = op.get_bind()
    memories = connection.execute(
        sa.text(
            """
            SELECT
                id,
                current_conversation_id,
                current_convhub_branch_id,
                current_commit_id,
                current_context_package_id,
                working_user_id,
                memory_version
            FROM branch_memories
            """
        )
    ).fetchall()

    for row in memories:
        memory_id = row[0]
        conversation_id = row[1]
        convhub_branch_id = row[2]
        commit_id = row[3]
        context_package_id = row[4]
        user_id = row[5]
        memory_version = row[6] or 1

        if (
            conversation_id is None
            and convhub_branch_id is None
            and commit_id is None
            and context_package_id is None
        ):
            continue

        if commit_id is not None:
            sync_type = "local_commit"
        elif context_package_id is not None:
            sync_type = "restore"
        else:
            sync_type = "attach_repository"

        record_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO branch_sync_records (
                    id,
                    branch_memory_id,
                    conversation_id,
                    convhub_branch_id,
                    commit_id,
                    context_package_id,
                    user_id,
                    sync_type,
                    sync_version,
                    created_at
                ) VALUES (
                    :record_id,
                    :memory_id,
                    :conversation_id,
                    :convhub_branch_id,
                    :commit_id,
                    :context_package_id,
                    :user_id,
                    :sync_type,
                    :sync_version,
                    now()
                )
                """
            ),
            {
                "record_id": record_id,
                "memory_id": memory_id,
                "conversation_id": conversation_id,
                "convhub_branch_id": convhub_branch_id,
                "commit_id": commit_id,
                "context_package_id": context_package_id,
                "user_id": user_id,
                "sync_type": sync_type,
                "sync_version": memory_version,
            },
        )
        connection.execute(
            sa.text(
                """
                UPDATE branch_memories
                SET latest_sync_record_id = :record_id
                WHERE id = :memory_id
                """
            ),
            {"record_id": record_id, "memory_id": memory_id},
        )

    op.create_foreign_key(
        "fk_branch_memories_latest_sync_record_id",
        "branch_memories",
        "branch_sync_records",
        ["latest_sync_record_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "branch_memories_working_user_id_fkey",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "branch_memories_current_context_package_id_fkey",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "branch_memories_current_commit_id_fkey",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "branch_memories_current_convhub_branch_id_fkey",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "branch_memories_current_conversation_id_fkey",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_column("branch_memories", "working_user_id")
    op.drop_column("branch_memories", "current_context_package_id")
    op.drop_column("branch_memories", "current_commit_id")
    op.drop_column("branch_memories", "current_convhub_branch_id")
    op.drop_column("branch_memories", "current_conversation_id")
    op.drop_column("branch_memories", "last_push_at")
    op.drop_column("branch_memories", "last_pull_at")


def downgrade() -> None:
    op.add_column(
        "branch_memories",
        sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("current_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("current_convhub_branch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("current_commit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("current_context_package_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "branch_memories",
        sa.Column("working_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "branch_memories_current_conversation_id_fkey",
        "branch_memories",
        "conversations",
        ["current_conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "branch_memories_current_convhub_branch_id_fkey",
        "branch_memories",
        "conversations",
        ["current_convhub_branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "branch_memories_current_commit_id_fkey",
        "branch_memories",
        "conversation_commits",
        ["current_commit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "branch_memories_current_context_package_id_fkey",
        "branch_memories",
        "context_packages",
        ["current_context_package_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "branch_memories_working_user_id_fkey",
        "branch_memories",
        "users",
        ["working_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    memories = connection.execute(sa.text("SELECT id FROM branch_memories")).fetchall()
    for (memory_id,) in memories:
        latest = connection.execute(
            sa.text(
                """
                SELECT
                    conversation_id,
                    convhub_branch_id,
                    commit_id,
                    context_package_id,
                    user_id
                FROM branch_sync_records
                WHERE branch_memory_id = :memory_id
                ORDER BY sync_version DESC
                LIMIT 1
                """
            ),
            {"memory_id": memory_id},
        ).first()
        if latest is None:
            continue
        connection.execute(
            sa.text(
                """
                UPDATE branch_memories
                SET
                    current_conversation_id = :conversation_id,
                    current_convhub_branch_id = :convhub_branch_id,
                    current_commit_id = :commit_id,
                    current_context_package_id = :context_package_id,
                    working_user_id = :user_id
                WHERE id = :memory_id
                """
            ),
            {
                "memory_id": memory_id,
                "conversation_id": latest[0],
                "convhub_branch_id": latest[1],
                "commit_id": latest[2],
                "context_package_id": latest[3],
                "user_id": latest[4],
            },
        )

    op.drop_constraint(
        "fk_branch_memories_latest_sync_record_id",
        "branch_memories",
        type_="foreignkey",
    )
    op.drop_column("branch_memories", "latest_sync_record_id")
    op.drop_index(
        "ix_branch_sync_records_branch_memory_id_sync_version",
        table_name="branch_sync_records",
    )
    op.drop_index("ix_branch_sync_records_branch_memory_id", table_name="branch_sync_records")
    op.drop_table("branch_sync_records")
    branch_sync_type_enum.drop(op.get_bind(), checkfirst=True)
