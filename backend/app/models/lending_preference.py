from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

DEFAULT_MINIMUM_RESERVED_CREDITS = Decimal("500.00")


class LendingPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lending_preferences"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_lending_preferences_workspace_user"),
        Index("ix_lending_preferences_workspace_id", "workspace_id"),
        Index("ix_lending_preferences_user_id", "user_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    auto_share_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    monthly_share_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
    )
    minimum_reserved_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=DEFAULT_MINIMUM_RESERVED_CREDITS,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(lazy="selectin")
