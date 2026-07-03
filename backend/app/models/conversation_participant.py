from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import ConversationParticipantRole

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.user import User


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        Index("ix_conversation_participants_conversation_id", "conversation_id"),
        Index("ix_conversation_participants_user_id", "user_id"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[ConversationParticipantRole] = mapped_column(
        pg_enum(ConversationParticipantRole, name="conversation_participant_role"),
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="participants", lazy="selectin"
    )
    user: Mapped[User] = relationship(lazy="selectin")
