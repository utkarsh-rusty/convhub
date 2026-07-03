from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ai_account import AIAccount
    from app.models.conversation import Conversation
    from app.models.invitation import Invitation
    from app.models.message import Message
    from app.models.refresh_token import RefreshToken
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    workspace_memberships: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="created_by",
        foreign_keys="Conversation.created_by_id",
        lazy="selectin",
    )
    owned_conversations: Mapped[list[Conversation]] = relationship(
        back_populates="owner",
        foreign_keys="Conversation.owner_id",
        lazy="selectin",
    )
    owned_workspaces: Mapped[list[Workspace]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="author",
        lazy="selectin",
    )
    ai_accounts: Mapped[list[AIAccount]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    sent_invitations: Mapped[list[Invitation]] = relationship(
        back_populates="invited_by",
        lazy="selectin",
    )
