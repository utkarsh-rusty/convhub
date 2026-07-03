from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RoutingPolicyType


class RoutingAccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    display_name: str
    is_active: bool
    priority: int
    monthly_spent: Decimal
    default_model: str | None


class RoutingPreview(BaseModel):
    selected_account_id: UUID | None
    selected_provider: str
    selected_model: str
    policy_used: RoutingPolicyType
    routing_policy: RoutingPolicyType
    score: Decimal | None
    decision_reason: str


class RoutingSettingsResponse(BaseModel):
    routing_policy: RoutingPolicyType
    active_accounts: list[RoutingAccountSummary]
    preview: RoutingPreview


class RoutingSettingsUpdate(BaseModel):
    routing_policy: RoutingPolicyType
