from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch_memory import BranchMemory
    from app.models.repository import Repository


class RepositoryBranch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repository_branches"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_repository_branches_repository_id_name"),
        Index("ix_repository_branches_repository_id", "repository_id"),
    )

    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    repository: Mapped[Repository] = relationship(back_populates="branches", lazy="selectin")
    memory: Mapped[BranchMemory | None] = relationship(
        back_populates="repository_branch",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
