from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class WorkspaceDemoSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_demo_settings"
    __table_args__ = (
        Index("ix_workspace_demo_settings_workspace_id", "workspace_id", unique=True),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    pricing_profile: Mapped[PricingProfileType] = mapped_column(
        pg_enum(PricingProfileType, name="pricing_profile_type"),
        nullable=False,
        default=PricingProfileType.PRODUCTION,
    )
    provider_simulation: Mapped[ProviderSimulationMode] = mapped_column(
        pg_enum(ProviderSimulationMode, name="provider_simulation_mode"),
        nullable=False,
        default=ProviderSimulationMode.NORMAL,
    )
    routing_override_mode: Mapped[RoutingOverrideMode] = mapped_column(
        pg_enum(RoutingOverrideMode, name="routing_override_mode"),
        nullable=False,
        default=RoutingOverrideMode.NORMAL,
    )
    routing_override_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped[Workspace] = relationship(lazy="selectin")
