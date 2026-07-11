from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository_branch import RepositoryBranch


class RepositoryMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical deterministic repository memory artifact for a repository branch."""

    __tablename__ = "repository_memories"
    __table_args__ = (
        Index("ix_repository_memories_repository_branch_id", "repository_branch_id", unique=True),
    )

    repository_branch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repository_branches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    memory_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latest_commit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_context_package_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("context_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_workspace_session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("developer_workspace_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    json_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    repository_branch: Mapped[RepositoryBranch] = relationship(lazy="noload")
