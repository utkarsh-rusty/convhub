from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import BranchSyncType
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch_memory import BranchMemory
    from app.models.context_package import ContextPackage
    from app.models.conversation import Conversation
    from app.models.conversation_commit import ConversationCommit
    from app.models.user import User


class BranchSyncRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "branch_sync_records"
    __table_args__ = (
        Index("ix_branch_sync_records_branch_memory_id", "branch_memory_id"),
        Index(
            "ix_branch_sync_records_branch_memory_id_sync_version",
            "branch_memory_id",
            "sync_version",
            unique=True,
        ),
    )

    branch_memory_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("branch_memories.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    convhub_branch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    commit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_package_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("context_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sync_type: Mapped[BranchSyncType] = mapped_column(
        pg_enum(BranchSyncType, name="branch_sync_type"),
        nullable=False,
    )
    sync_version: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    branch_memory: Mapped[BranchMemory] = relationship(
        back_populates="sync_records",
        foreign_keys=[branch_memory_id],
        lazy="selectin",
    )
    conversation: Mapped[Conversation | None] = relationship(
        foreign_keys=[conversation_id],
        lazy="selectin",
    )
    convhub_branch: Mapped[Conversation | None] = relationship(
        foreign_keys=[convhub_branch_id],
        lazy="selectin",
    )
    commit: Mapped[ConversationCommit | None] = relationship(
        foreign_keys=[commit_id],
        lazy="selectin",
    )
    context_package: Mapped[ContextPackage | None] = relationship(
        foreign_keys=[context_package_id],
        lazy="selectin",
    )
    user: Mapped[User | None] = relationship(
        foreign_keys=[user_id],
        lazy="selectin",
    )
