from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.context_package import ContextPackage
    from app.models.conversation_commit import ConversationCommit
    from app.models.conversation_participant import ConversationParticipant
    from app.models.message import Message
    from app.models.project import Project
    from app.models.repository import Repository
    from app.models.user import User
    from app.models.workspace import Workspace

DEFAULT_CONVERSATION_TITLE = "Untitled Conversation"


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_workspace_id", "workspace_id"),
        Index("ix_conversations_project_id", "project_id"),
        Index("ix_conversations_parent_conversation_id", "parent_conversation_id"),
        Index("ix_conversations_owner_id", "owner_id"),
        Index("ix_conversations_restored_from_package_id", "restored_from_package_id"),
        Index("ix_conversations_repository_id", "repository_id"),
        Index("ix_conversations_coding_enabled", "coding_enabled"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    coding_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    repository_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=DEFAULT_CONVERSATION_TITLE,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parent_conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    branch_from_message_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    restored_from_package_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("context_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_from_commit_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_from_conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="conversations", lazy="selectin")
    project: Mapped[Project] = relationship(back_populates="conversations", lazy="selectin")
    repository: Mapped[Repository | None] = relationship(
        back_populates="conversations",
        foreign_keys=[repository_id],
        lazy="selectin",
    )
    created_by: Mapped[User | None] = relationship(
        back_populates="conversations",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )
    owner: Mapped[User] = relationship(
        back_populates="owned_conversations",
        foreign_keys=[owner_id],
        lazy="selectin",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Message.conversation_id",
    )
    participants: Mapped[list[ConversationParticipant]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    parent_conversation: Mapped[Conversation | None] = relationship(
        "Conversation",
        remote_side="Conversation.id",
        foreign_keys=[parent_conversation_id],
        lazy="selectin",
    )
    restored_from_package: Mapped[ContextPackage | None] = relationship(
        foreign_keys=[restored_from_package_id],
        lazy="selectin",
    )
    restored_from_commit: Mapped[ConversationCommit | None] = relationship(
        foreign_keys=[restored_from_commit_id],
        lazy="selectin",
    )
    restored_from_conversation: Mapped[Conversation | None] = relationship(
        "Conversation",
        remote_side="Conversation.id",
        foreign_keys=[restored_from_conversation_id],
        lazy="selectin",
    )
    restored_by: Mapped[User | None] = relationship(
        foreign_keys=[restored_by_user_id],
        lazy="selectin",
    )
