from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AIProviderName = Literal["mock", "anthropic", "ollama", "openai", "gemini", "groq"]


class AIAccountCreate(BaseModel):
    provider: AIProviderName
    display_name: str = Field(min_length=1, max_length=255)
    api_key: str | None = Field(
        default=None,
        description="Provider API key; not required for Ollama",
    )
    is_active: bool = True
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    priority: int = Field(default=0, ge=0)
    default_model: str | None = Field(
        default=None,
        max_length=255,
        description="Optional provider-specific default model override",
    )

    @model_validator(mode="after")
    def require_api_key_for_credential_providers(self) -> "AIAccountCreate":
        if self.provider != "ollama" and not self.api_key:
            raise ValueError("API key is required for this provider")
        return self


class AIAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=0)
    default_model: str | None = Field(default=None, max_length=255)


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
    default_model: str | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    request_count: int = 0
    credits_used: Decimal = Decimal("0")


class AIAccountTestResponse(BaseModel):
    success: bool
    message: str
