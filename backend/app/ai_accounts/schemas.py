from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AIProviderName = Literal["mock", "anthropic"]


class AIAccountCreate(BaseModel):
    provider: AIProviderName
    display_name: str = Field(min_length=1, max_length=255)
    api_key: str = Field(min_length=1, description="Provider API key; never stored in plaintext")
    is_active: bool = True
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    priority: int = Field(default=0, ge=0)


class AIAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=0)


class AIAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    provider: str
    display_name: str
    is_active: bool
    monthly_budget: Decimal | None
    monthly_spent: Decimal
    priority: int
    created_at: datetime
    updated_at: datetime


class AIAccountTestResponse(BaseModel):
    success: bool
    message: str
