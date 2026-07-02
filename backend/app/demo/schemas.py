from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.demo.constants import DemoPersona
from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)


class DemoConfigResponse(BaseModel):
    enabled: bool


class DemoUserResponse(BaseModel):
    persona: DemoPersona
    name: str
    email: str
    role: str


class DemoUsersResponse(BaseModel):
    workspace_slug: str
    users: list[DemoUserResponse]


class DemoLoginRequest(BaseModel):
    persona: DemoPersona


class DemoLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    workspace_id: UUID | None = None
    workspace_slug: str | None = None


class DemoSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    pricing_profile: PricingProfileType
    provider_simulation: ProviderSimulationMode
    routing_override_mode: RoutingOverrideMode
    routing_override_account_id: UUID | None


class PricingProfileUpdate(BaseModel):
    pricing_profile: PricingProfileType


class ProviderSimulationUpdate(BaseModel):
    provider_simulation: ProviderSimulationMode


class RoutingOverrideUpdate(BaseModel):
    routing_override_mode: RoutingOverrideMode
    routing_override_account_id: UUID | None = None


class SetUserCreditsRequest(BaseModel):
    user_id: UUID
    remaining_credits: Decimal = Field(ge=0)


class UserBudgetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    monthly_credit_limit: Decimal
    remaining_credits: Decimal
    used_credits: Decimal
    borrowed_credits: Decimal
    lent_credits: Decimal


class DemoEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    message: str
    created_at: datetime


class DemoEventsResponse(BaseModel):
    items: list[DemoEventResponse]


class DemoActionResponse(BaseModel):
    message: str
    affected_count: int | None = None


class UserCreditsResponse(BaseModel):
    budget: UserBudgetSummary
