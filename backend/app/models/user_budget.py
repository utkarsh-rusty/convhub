from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class UserBudget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_budgets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_user_budgets_workspace_user"),
        Index("ix_user_budgets_workspace_id", "workspace_id"),
        Index("ix_user_budgets_user_id", "user_id"),
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
    monthly_credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    used_credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    borrowed_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
    )
    lent_credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    remaining_credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reset_date: Mapped[date] = mapped_column(Date, nullable=False)

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(lazy="selectin")
