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
    from app.models.branch_sync_record import BranchSyncRecord
    from app.models.repository_branch import RepositoryBranch


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
    latest_sync_record_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("branch_sync_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_sync_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[BranchMemorySyncStatus] = mapped_column(
        pg_enum(BranchMemorySyncStatus, name="branch_memory_sync_status"),
        nullable=False,
        default=BranchMemorySyncStatus.NOT_SYNCED,
    )

    repository_branch: Mapped[RepositoryBranch] = relationship(
        back_populates="memory",
        lazy="selectin",
    )
    latest_sync_record: Mapped[BranchSyncRecord | None] = relationship(
        foreign_keys=[latest_sync_record_id],
        lazy="selectin",
    )
    sync_records: Mapped[list[BranchSyncRecord]] = relationship(
        back_populates="branch_memory",
        foreign_keys="BranchSyncRecord.branch_memory_id",
        lazy="selectin",
        order_by="BranchSyncRecord.sync_version.desc()",
    )
