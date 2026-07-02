from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class AIAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_accounts"
    __table_args__ = (
        Index("ix_ai_accounts_workspace_id", "workspace_id"),
        Index("ix_ai_accounts_workspace_id_provider", "workspace_id", "provider"),
        Index("ix_ai_accounts_owner_user_id", "owner_user_id"),
        Index("ix_ai_accounts_workspace_id_owner_user_id", "workspace_id", "owner_user_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    monthly_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_spent: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="ai_accounts", lazy="selectin")
    owner: Mapped[User] = relationship(back_populates="ai_accounts", lazy="selectin")
