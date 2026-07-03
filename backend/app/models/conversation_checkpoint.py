from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.conversation_commit import ConversationCommit
    from app.models.message import Message


class ConversationCheckpoint(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_checkpoints"
    __table_args__ = (
        Index("ix_conversation_checkpoints_conversation_id", "conversation_id"),
        Index("ix_conversation_checkpoints_latest_message_id", "latest_message_id"),
        Index("ix_conversation_checkpoints_parent_checkpoint_id", "parent_checkpoint_id"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    latest_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_checkpoint_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_checkpoints.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(lazy="selectin")
    latest_message: Mapped[Message] = relationship(
        foreign_keys=[latest_message_id],
        lazy="selectin",
    )
    parent_checkpoint: Mapped[ConversationCheckpoint | None] = relationship(
        remote_side="ConversationCheckpoint.id",
        foreign_keys=[parent_checkpoint_id],
        lazy="selectin",
    )
    commit: Mapped[ConversationCommit | None] = relationship(
        back_populates="checkpoint",
        uselist=False,
        lazy="selectin",
    )
