from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.external_ai_session import ExternalAISession


class TranscriptSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Deterministic assembled transcript for one external AI session."""

    __tablename__ = "transcript_snapshots"
    __table_args__ = (
        Index(
            "ix_transcript_snapshots_external_ai_session_id",
            "external_ai_session_id",
            unique=True,
        ),
    )

    external_ai_session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    external_ai_session: Mapped[ExternalAISession] = relationship(
        back_populates="transcript_snapshot",
        lazy="noload",
    )
