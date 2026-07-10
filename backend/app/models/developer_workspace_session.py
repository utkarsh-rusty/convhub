from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import DeveloperWorkspaceSessionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.project import Project
    from app.models.repository import Repository
    from app.models.repository_branch import RepositoryBranch
    from app.models.user import User
    from app.models.workspace import Workspace


class DeveloperWorkspaceSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "developer_workspace_sessions"
    __table_args__ = (
        Index("ix_developer_workspace_sessions_workspace_id", "workspace_id"),
        Index("ix_developer_workspace_sessions_repository_id", "repository_id"),
        Index("ix_developer_workspace_sessions_repository_branch_id", "repository_branch_id"),
        Index("ix_developer_workspace_sessions_conversation_id", "conversation_id"),
        Index("ix_developer_workspace_sessions_user_id", "user_id"),
        Index("ix_developer_workspace_sessions_status", "status"),
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
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[DeveloperWorkspaceSessionStatus] = mapped_column(
        pg_enum(DeveloperWorkspaceSessionStatus, name="developer_workspace_session_status"),
        nullable=False,
        default=DeveloperWorkspaceSessionStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    working_directory: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
    project: Mapped[Project] = relationship(lazy="selectin")
    repository: Mapped[Repository] = relationship(lazy="selectin")
    repository_branch: Mapped[RepositoryBranch] = relationship(lazy="selectin")
    conversation: Mapped[Conversation] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(lazy="selectin")
