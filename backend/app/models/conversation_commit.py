from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.context_package import ContextPackage
    from app.models.conversation import Conversation
    from app.models.conversation_checkpoint import ConversationCheckpoint
    from app.models.message import Message
    from app.models.user import User


class ConversationCommit(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_commits"
    __table_args__ = (
        Index("ix_conversation_commits_conversation_id", "conversation_id"),
        Index("ix_conversation_commits_commit_hash", "commit_hash", unique=True),
        Index("ix_conversation_commits_checkpoint_id", "checkpoint_id"),
        Index("ix_conversation_commits_parent_commit_id", "parent_commit_id"),
        Index("ix_conversation_commits_created_by_id", "created_by_id"),
    )

    commit_hash: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    checkpoint_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    latest_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_commit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(
        foreign_keys=[conversation_id],
        lazy="selectin",
    )
    checkpoint: Mapped[ConversationCheckpoint] = relationship(
        back_populates="commit",
        foreign_keys=[checkpoint_id],
        lazy="selectin",
    )
    latest_message: Mapped[Message] = relationship(
        foreign_keys=[latest_message_id],
        lazy="selectin",
    )
    parent_commit: Mapped[ConversationCommit | None] = relationship(
        remote_side="ConversationCommit.id",
        foreign_keys=[parent_commit_id],
        lazy="selectin",
    )
    created_by: Mapped[User] = relationship(lazy="selectin")
    context_package: Mapped[ContextPackage | None] = relationship(
        back_populates="commit",
        uselist=False,
        lazy="selectin",
    )
