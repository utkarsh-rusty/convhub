from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import RepositoryProvider, RepositoryVisibility
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.project import Project
    from app.models.repository_branch import RepositoryBranch
    from app.models.user import User
    from app.models.workspace import Workspace


class Repository(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (
        Index("ix_repositories_workspace_id", "workspace_id"),
        Index("ix_repositories_project_id", "project_id"),
        Index("ix_repositories_created_by_id", "created_by_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[RepositoryProvider] = mapped_column(
        pg_enum(RepositoryProvider, name="repository_provider"),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    remote_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    visibility: Mapped[RepositoryVisibility] = mapped_column(
        pg_enum(RepositoryVisibility, name="repository_visibility"),
        nullable=False,
        default=RepositoryVisibility.PRIVATE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
    project: Mapped[Project] = relationship(back_populates="repositories", lazy="selectin")
    created_by: Mapped[User | None] = relationship(
        foreign_keys=[created_by_id],
        lazy="selectin",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="repository",
        lazy="selectin",
    )
    branches: Mapped[list["RepositoryBranch"]] = relationship(
        back_populates="repository",
        lazy="selectin",
    )
