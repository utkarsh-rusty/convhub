from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.external_ai_session import ExternalAISession


class TranscriptChunk(UUIDPrimaryKeyMixin, Base):
    """Append-only raw transcript fragment for an external AI session."""

    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint(
            "external_ai_session_id",
            "sequence_number",
            name="uq_transcript_chunks_session_sequence",
        ),
        Index("ix_transcript_chunks_external_ai_session_id", "external_ai_session_id"),
        Index(
            "ix_transcript_chunks_session_sequence",
            "external_ai_session_id",
            "sequence_number",
        ),
    )

    external_ai_session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    external_ai_session: Mapped[ExternalAISession] = relationship(
        back_populates="chunks",
        lazy="noload",
    )
