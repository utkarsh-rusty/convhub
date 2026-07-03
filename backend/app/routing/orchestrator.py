from __future__ import annotations

from typing import TYPE_CHECKING

from app.routing.context import RoutingContext
from app.routing.engine import RoutingEngine
from app.routing.sender_resolution import SenderFirstAccountResolver

if TYPE_CHECKING:
    from app.routing.decision import RoutingDecision


class AccountRoutingOrchestrator:
    """Ownership-first routing: policy runs only on a single owner's accounts."""

    def __init__(
        self,
        routing_engine: RoutingEngine,
        sender_resolver: SenderFirstAccountResolver | None = None,
    ) -> None:
        self.routing_engine = routing_engine
        self.sender_resolver = sender_resolver or SenderFirstAccountResolver()

    async def select(self, context: RoutingContext) -> RoutingDecision:

        owner_id = context.scoped_owner_id or context.requesting_user.id
        budget_settings = await self.routing_engine.budget_service.get_workspace_budget_settings(
            context.workspace.id,
        )
        policy_type = budget_settings.routing_policy

        accounts = await self.routing_engine.load_user_accounts(context.workspace.id, owner_id)
        healthy = self.routing_engine.filter_healthy_accounts(accounts, budget_settings, context)
        monthly_usage = await self.routing_engine.load_monthly_usage(context.workspace.id)

        if not healthy:
            return self.routing_engine.fallback_decision(
                context,
                policy_type,
                f"No eligible AI accounts for owner {owner_id}",
            )

        override_decision = await self.routing_engine.routing_override.try_override(
            context,
            healthy,
            policy_type=policy_type,
            monthly_usage=monthly_usage,
        )
        if override_decision is not None:
            return override_decision

        if owner_id == context.requesting_user.id:
            sender_score = self.sender_resolver.try_resolve(
                context,
                healthy,
                monthly_usage=monthly_usage,
            )
            if sender_score is not None:
                return await self.routing_engine.build_decision(
                    sender_score,
                    policy_type=policy_type,
                    decision_reason=sender_score.reason,
                )

        policy = self.routing_engine.get_policy(policy_type)
        scored = policy.choose_account(context, healthy, monthly_usage=monthly_usage)
        if scored is None:
            return self.routing_engine.fallback_decision(
                context,
                policy_type,
                f"Routing policy returned no candidate for owner {owner_id}",
            )

        return await self.routing_engine.build_decision(
            scored,
            policy_type=policy_type,
            decision_reason=f"Owner routing via {policy_type.value}; {scored.reason}",
        )

    async def preview(self, context: RoutingContext) -> RoutingDecision:
        return await self.select(context)
