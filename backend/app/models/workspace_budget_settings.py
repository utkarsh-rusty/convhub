from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import RoutingPolicyType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.resource_management.constants import DEFAULT_MONTHLY_CREDIT_LIMIT

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class WorkspaceBudgetSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_budget_settings"
    __table_args__ = (
        Index("ix_workspace_budget_settings_workspace_id", "workspace_id", unique=True),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    monthly_default_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=DEFAULT_MONTHLY_CREDIT_LIMIT,
    )
    allow_credit_borrowing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_emergency_pool: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_local_models: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hard_budget_enforcement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    routing_policy: Mapped[RoutingPolicyType] = mapped_column(
        pg_enum(RoutingPolicyType, name="routing_policy_type"),
        nullable=False,
        default=RoutingPolicyType.OWNER_FIRST,
    )

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
