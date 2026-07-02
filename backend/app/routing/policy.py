from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.models.ai_account import AIAccount
from app.models.enums import RoutingPolicyType
from app.routing.context import RoutingContext
from app.routing.decision import RoutingScore
from app.routing.health import ProviderHealth

FREE_PROVIDERS = {"ollama", "mock"}
PAID_PROVIDER_ORDER = {"ollama": 0, "mock": 1, "anthropic": 2, "openai": 3, "gemini": 4, "groq": 5}


class RoutingPolicy(ABC):
    policy_type: RoutingPolicyType

    @abstractmethod
    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        """Rank candidates and return the best scoring account."""


class PriorityPolicy(RoutingPolicy):
    policy_type = RoutingPolicyType.PRIORITY

    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        _ = context, monthly_usage
        if not candidates:
            return None
        best = min(candidates, key=lambda item: (item.account.priority, item.account.created_at))
        return RoutingScore(
            account=best.account,
            score=Decimal(str(best.account.priority)),
            reason=f"Selected by priority ({best.account.priority})",
        )


class OwnerFirstPolicy(RoutingPolicy):
    policy_type = RoutingPolicyType.OWNER_FIRST

    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        if not candidates:
            return None

        if context.requesting_user.id == context.workspace.owner_id:
            return PriorityPolicy().choose_account(context, candidates, monthly_usage=monthly_usage)

        return BalancedPolicy().choose_account(context, candidates, monthly_usage=monthly_usage)


class BalancedPolicy(RoutingPolicy):
    policy_type = RoutingPolicyType.BALANCED

    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        _ = context
        if not candidates:
            return None
        best = min(
            candidates,
            key=lambda item: (
                monthly_usage.get(str(item.account.id), item.account.monthly_spent),
                item.account.priority,
                item.account.created_at,
            ),
        )
        spend = monthly_usage.get(str(best.account.id), best.account.monthly_spent)
        return RoutingScore(
            account=best.account,
            score=spend,
            reason=f"Selected by lowest monthly spend ({spend})",
        )


class LowestUsagePolicy(RoutingPolicy):
    policy_type = RoutingPolicyType.LOWEST_USAGE

    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        _ = context
        if not candidates:
            return None
        best = min(
            candidates,
            key=lambda item: (
                monthly_usage.get(str(item.account.id), Decimal("0")),
                item.account.priority,
            ),
        )
        usage = monthly_usage.get(str(best.account.id), Decimal("0"))
        return RoutingScore(
            account=best.account,
            score=usage,
            reason=f"Selected by lowest AI request cost this month ({usage})",
        )


class CheapestPolicy(RoutingPolicy):
    policy_type = RoutingPolicyType.CHEAPEST

    def choose_account(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        _ = context, monthly_usage
        if not candidates:
            return None

        def provider_rank(account: AIAccount) -> int:
            return PAID_PROVIDER_ORDER.get(account.provider.lower(), 99)

        best = min(
            candidates,
            key=lambda item: (provider_rank(item.account), item.account.priority, item.account.created_at),
        )
        return RoutingScore(
            account=best.account,
            score=Decimal(str(provider_rank(best.account))),
            reason=f"Selected cheapest provider ({best.account.provider})",
        )


POLICY_REGISTRY: dict[RoutingPolicyType, RoutingPolicy] = {
    RoutingPolicyType.OWNER_FIRST: OwnerFirstPolicy(),
    RoutingPolicyType.BALANCED: BalancedPolicy(),
    RoutingPolicyType.LOWEST_USAGE: LowestUsagePolicy(),
    RoutingPolicyType.CHEAPEST: CheapestPolicy(),
    RoutingPolicyType.PRIORITY: PriorityPolicy(),
}


def get_policy(policy_type: RoutingPolicyType) -> RoutingPolicy:
    return POLICY_REGISTRY[policy_type]
