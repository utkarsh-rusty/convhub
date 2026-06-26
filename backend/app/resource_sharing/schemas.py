from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LendingPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    user_id: UUID
    auto_share_enabled: bool
    monthly_share_limit: Decimal
    minimum_reserved_credits: Decimal
    priority: int
    created_at: datetime
    updated_at: datetime


class LendingPreferenceUpdate(BaseModel):
    auto_share_enabled: bool | None = None
    monthly_share_limit: Decimal | None = Field(default=None, ge=0)
    minimum_reserved_credits: Decimal | None = Field(default=None, ge=0)
    priority: int | None = None


class WorkspaceSharingMemberResponse(BaseModel):
    user_id: UUID
    user_name: str
    user_email: str
    auto_share_enabled: bool
    remaining_credits: Decimal
    monthly_share_limit: Decimal
    minimum_reserved_credits: Decimal
    borrowed_credits: Decimal
    lent_credits: Decimal
    priority: int


class WorkspaceSharingOverviewResponse(BaseModel):
    members: list[WorkspaceSharingMemberResponse]
