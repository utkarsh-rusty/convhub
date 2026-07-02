from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy", "degraded"]
    detail: str | None = None


class ProviderHealthRow(BaseModel):
    account_id: UUID
    provider: str
    model: str
    display_name: str
    owner_name: str | None = None
    healthy: bool
    last_used_at: datetime | None
    request_count: int
    credits_used: Decimal


class SystemStatusResponse(BaseModel):
    environment: str
    demo_mode: bool
    components: list[ComponentStatus]
    providers: list[ProviderHealthRow]
