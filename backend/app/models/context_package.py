from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.conversation_commit import ConversationCommit


class ContextPackage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "context_packages"
    __table_args__ = (
        Index("ix_context_packages_conversation_id", "conversation_id"),
        Index("ix_context_packages_commit_id", "commit_id", unique=True),
    )

    commit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    statistics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    search_keywords_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    commit: Mapped[ConversationCommit] = relationship(
        back_populates="context_package",
        foreign_keys=[commit_id],
        lazy="selectin",
    )
    conversation: Mapped[Conversation] = relationship(lazy="selectin")
