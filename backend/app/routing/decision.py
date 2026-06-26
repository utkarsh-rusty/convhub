from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.ai_account import AIAccount
from app.models.enums import RoutingPolicyType


@dataclass(frozen=True)
class RoutingScore:
    account: AIAccount
    score: Decimal
    reason: str


@dataclass(frozen=True)
class RoutingDecision:
    selected_account: AIAccount | None
    selected_model: str
    policy_used: RoutingPolicyType
    score: Decimal | None
    decision_reason: str
    credentials: dict[str, str] | None = None
