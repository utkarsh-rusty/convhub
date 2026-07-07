from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import BranchMemorySyncStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.context_package import ContextPackage
    from app.models.conversation import Conversation
    from app.models.conversation_commit import ConversationCommit
    from app.models.repository_branch import RepositoryBranch
    from app.models.user import User


class BranchMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branch_memories"
    __table_args__ = (
        Index("ix_branch_memories_repository_branch_id", "repository_branch_id", unique=True),
    )

    repository_branch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repository_branches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_convhub_branch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_commit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_context_package_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("context_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
    working_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sync_status: Mapped[BranchMemorySyncStatus] = mapped_column(
        pg_enum(BranchMemorySyncStatus, name="branch_memory_sync_status"),
        nullable=False,
        default=BranchMemorySyncStatus.NOT_SYNCED,
    )
    last_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_pull_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository_branch: Mapped[RepositoryBranch] = relationship(
        back_populates="memory",
        lazy="selectin",
    )
    current_conversation: Mapped[Conversation | None] = relationship(
        foreign_keys=[current_conversation_id],
        lazy="selectin",
    )
    current_convhub_branch: Mapped[Conversation | None] = relationship(
        foreign_keys=[current_convhub_branch_id],
        lazy="selectin",
    )
    current_commit: Mapped[ConversationCommit | None] = relationship(
        foreign_keys=[current_commit_id],
        lazy="selectin",
    )
    current_context_package: Mapped[ContextPackage | None] = relationship(
        foreign_keys=[current_context_package_id],
        lazy="selectin",
    )
    working_user: Mapped[User | None] = relationship(
        foreign_keys=[working_user_id],
        lazy="selectin",
    )
