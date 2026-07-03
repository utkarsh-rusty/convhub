from __future__ import annotations

import asyncio
import random
from typing import Protocol

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider
from app.models.enums import ProviderSimulationMode, RoutingOverrideMode
from app.routing.context import RoutingContext
from app.routing.decision import RoutingDecision
from app.routing.health import ProviderHealth


class RoutingOverrideProvider(Protocol):
    async def try_override(
        self,
        context: RoutingContext,
        healthy: list[ProviderHealth],
        *,
        policy_type,
        monthly_usage: dict[str, object],
    ) -> RoutingDecision | None: ...


class NoOpRoutingOverride:
    async def try_override(self, *args, **kwargs) -> RoutingDecision | None:
        return None


class DemoRoutingOverride:
    def __init__(self, ai_account_service) -> None:
        self.ai_account_service = ai_account_service

    async def try_override(
        self,
        context: RoutingContext,
        healthy: list[ProviderHealth],
        *,
        policy_type,
        monthly_usage: dict[str, object],
    ) -> RoutingDecision | None:
        from app.demo.context import get_demo_runtime

        runtime = get_demo_runtime()
        if runtime is None or runtime.workspace_id != context.workspace.id:
            return None

        mode = runtime.routing_override_mode
        if mode == RoutingOverrideMode.NORMAL:
            return None

        if not healthy:
            return None

        ordered = sorted(healthy, key=lambda item: (item.account.priority, item.account.created_at))
        selected: ProviderHealth | None = None

        if mode == RoutingOverrideMode.FIRST_ACCOUNT:
            selected = ordered[0]
        elif mode == RoutingOverrideMode.SECOND_ACCOUNT:
            selected = ordered[1] if len(ordered) > 1 else ordered[0]
        elif mode == RoutingOverrideMode.RANDOM:
            selected = random.choice(ordered)
        elif mode == RoutingOverrideMode.SPECIFIC_ACCOUNT:
            if runtime.routing_override_account_id is None:
                return None
            for item in ordered:
                if item.account.id == runtime.routing_override_account_id:
                    selected = item
                    break

        if selected is None:
            return None

        account = selected.account
        model = self.ai_account_service.resolve_model(account.provider, account)
        credentials = await self.ai_account_service.get_decrypted_credentials(account)

        return RoutingDecision(
            selected_account=account,
            selected_model=model,
            policy_used=policy_type,
            score=None,
            decision_reason=f"Demo routing override ({mode.value})",
            credentials=credentials,
        )


class SimulatedFailureProvider(AIProvider):
    def __init__(self, inner: AIProvider, mode: ProviderSimulationMode) -> None:
        self.inner = inner
        self.mode = mode

    async def generate(self, prompt_context: PromptContext, model: str):
        if self.mode == ProviderSimulationMode.TIMEOUT:
            raise asyncio.TimeoutError("Simulated provider timeout")
        if self.mode == ProviderSimulationMode.UNAUTHORIZED:
            raise PermissionError("Simulated 401 Unauthorized")
        if self.mode == ProviderSimulationMode.RATE_LIMIT:
            raise RuntimeError("Simulated 429 Rate Limit Exceeded")
        if self.mode == ProviderSimulationMode.SERVER_ERROR:
            raise RuntimeError("Simulated 500 Internal Server Error")
        return await self.inner.generate(prompt_context, model)
