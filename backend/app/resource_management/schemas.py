from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CreditTransactionType, RoutingPolicyType


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    monthly_credit_limit: Decimal
    used_credits: Decimal
    borrowed_credits: Decimal
    lent_credits: Decimal
    remaining_credits: Decimal
    reset_date: date
    created_at: datetime
    updated_at: datetime


class CreditTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    request_id: UUID | None
    from_user_id: UUID | None
    to_user_id: UUID | None
    transaction_type: CreditTransactionType
    amount: Decimal
    description: str
    created_at: datetime


class CreditTransactionListResponse(BaseModel):
    items: list[CreditTransactionResponse]
    total: int
    limit: int
    offset: int


class CreditHistoryQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class WorkspaceBudgetSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    monthly_default_credits: Decimal
    allow_credit_borrowing: bool
    allow_emergency_pool: bool
    allow_local_models: bool
    routing_policy: RoutingPolicyType
    created_at: datetime
    updated_at: datetime


class WorkspaceBudgetSettingsUpdate(BaseModel):
    monthly_default_credits: Decimal | None = Field(default=None, ge=0)
    allow_credit_borrowing: bool | None = None
    allow_emergency_pool: bool | None = None
    allow_local_models: bool | None = None
    routing_policy: RoutingPolicyType | None = None
