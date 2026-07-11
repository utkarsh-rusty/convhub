from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import ExternalAIProvider, ExternalAISessionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.repository import Repository
    from app.models.repository_branch import RepositoryBranch
    from app.models.transcript_chunk import TranscriptChunk
    from app.models.transcript_snapshot import TranscriptSnapshot
    from app.models.user import User


class ExternalAISession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Storage for external AI tool session metadata (no transcript parsing)."""

    __tablename__ = "external_ai_sessions"
    __table_args__ = (
        Index("ix_external_ai_sessions_repository_id", "repository_id"),
        Index("ix_external_ai_sessions_repository_branch_id", "repository_branch_id"),
        Index("ix_external_ai_sessions_conversation_id", "conversation_id"),
        Index("ix_external_ai_sessions_workspace_user_id", "workspace_user_id"),
        Index("ix_external_ai_sessions_status", "status"),
        Index("ix_external_ai_sessions_provider", "provider"),
    )

    provider: Mapped[ExternalAIProvider] = mapped_column(
        pg_enum(ExternalAIProvider, name="external_ai_provider"),
        nullable=False,
    )
    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    repository_branch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repository_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    machine_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ExternalAISessionStatus] = mapped_column(
        pg_enum(ExternalAISessionStatus, name="external_ai_session_status"),
        nullable=False,
        default=ExternalAISessionStatus.ACTIVE,
    )

    repository: Mapped[Repository] = relationship(lazy="noload")
    repository_branch: Mapped[RepositoryBranch] = relationship(lazy="noload")
    conversation: Mapped[Conversation | None] = relationship(lazy="noload")
    workspace_user: Mapped[User] = relationship(
        foreign_keys=[workspace_user_id],
        lazy="noload",
    )
    chunks: Mapped[list[TranscriptChunk]] = relationship(
        back_populates="external_ai_session",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="TranscriptChunk.sequence_number.asc()",
    )
    transcript_snapshot: Mapped[TranscriptSnapshot | None] = relationship(
        back_populates="external_ai_session",
        lazy="noload",
        cascade="all, delete-orphan",
        uselist=False,
    )
