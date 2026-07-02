from __future__ import annotations

from decimal import Decimal

from app.models.enums import RoutingPolicyType
from app.routing.context import RoutingContext
from app.routing.decision import RoutingScore
from app.routing.health import ProviderHealth
from app.routing.policy import PriorityPolicy


class SenderFirstAccountResolver:
    """Select the message sender's own AI accounts before broader routing."""

    def try_resolve(
        self,
        context: RoutingContext,
        candidates: list[ProviderHealth],
        *,
        monthly_usage: dict[str, Decimal],
    ) -> RoutingScore | None:
        sender_accounts = [
            candidate
            for candidate in candidates
            if candidate.account.owner_user_id
            == (context.scoped_owner_id or context.requesting_user.id)
        ]
        if not sender_accounts:
            return None

        scored = PriorityPolicy().choose_account(
            context,
            sender_accounts,
            monthly_usage=monthly_usage,
        )
        if scored is None:
            return None

        return RoutingScore(
            account=scored.account,
            score=scored.score,
            reason=f"Sender-first by owner priority ({scored.account.priority}); {scored.reason}",
        )
