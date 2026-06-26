from __future__ import annotations

from dataclasses import dataclass

from app.models.ai_account import AIAccount


@dataclass(frozen=True)
class ProviderHealth:
    account: AIAccount
    is_healthy: bool
    reason: str
