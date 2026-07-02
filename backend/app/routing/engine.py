from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_accounts.service import AIAccountService
from app.core.config import Settings
from app.core.credentials import CredentialEncryption
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.enums import AIRequestStatus, RoutingPolicyType
from app.models.workspace_budget_settings import WorkspaceBudgetSettings
from app.resource_management.budget_service import BudgetService
from app.routing.context import RoutingContext
from app.routing.decision import RoutingDecision
from app.routing.health import ProviderHealth
from app.routing.policy import FREE_PROVIDERS, get_policy
from app.demo.runtime import NoOpRoutingOverride, RoutingOverrideProvider


class RoutingEngine:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        encryption: CredentialEncryption,
        ai_account_service: AIAccountService,
        budget_service: BudgetService,
        routing_override: RoutingOverrideProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.encryption = encryption
        self.ai_account_service = ai_account_service
        self.budget_service = budget_service
        self.routing_override = routing_override or NoOpRoutingOverride()

    async def select(self, context: RoutingContext) -> RoutingDecision:
        budget_settings = await self.budget_service.get_workspace_budget_settings(
            context.workspace.id,
        )
        policy_type = budget_settings.routing_policy
        policy = get_policy(policy_type)

        accounts = await self._load_active_accounts(context.workspace.id)
        healthy = self._filter_accounts(accounts, budget_settings, context)
        monthly_usage = await self._load_monthly_usage(context.workspace.id)

        if not healthy:
            return self._fallback_decision(context, policy_type, "No eligible workspace AI accounts")

        override_decision = await self.routing_override.try_override(
            context,
            healthy,
            policy_type=policy_type,
            monthly_usage=monthly_usage,
        )
        if override_decision is not None:
            return override_decision

        scored = policy.choose_account(context, healthy, monthly_usage=monthly_usage)
        if scored is None:
            return self._fallback_decision(context, policy_type, "Policy returned no candidate")

        account = scored.account
        model = self.ai_account_service.resolve_model(account.provider, account)
        credentials = await self.ai_account_service.get_decrypted_credentials(account)

        return RoutingDecision(
            selected_account=account,
            selected_model=model,
            policy_used=policy_type,
            score=scored.score,
            decision_reason=scored.reason,
            credentials=credentials,
        )

    async def preview(self, context: RoutingContext) -> RoutingDecision:
        return await self.select(context)

    async def _load_active_accounts(self, workspace_id: UUID) -> list[AIAccount]:
        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == workspace_id,
                AIAccount.is_active.is_(True),
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        return list(result.scalars().all())

    def _filter_accounts(
        self,
        accounts: list[AIAccount],
        budget_settings: WorkspaceBudgetSettings,
        context: RoutingContext,
    ) -> list[ProviderHealth]:
        healthy: list[ProviderHealth] = []
        for account in accounts:
            if context.provider and account.provider != context.provider:
                continue
            if account.provider == "ollama" and not budget_settings.allow_local_models:
                continue
            health = self._check_credentials(account)
            if health.is_healthy:
                healthy.append(health)
        return healthy

    def _check_credentials(self, account: AIAccount) -> ProviderHealth:
        if account.provider in FREE_PROVIDERS:
            return ProviderHealth(account=account, is_healthy=True, reason="No credentials required")

        try:
            credentials = self.encryption.decrypt(account.encrypted_credentials)
        except ValueError:
            return ProviderHealth(
                account=account,
                is_healthy=False,
                reason="Invalid stored credentials",
            )

        api_key = credentials.get("api_key", "").strip()
        if not api_key:
            if self.settings.app_env == "development":
                fallback_key = self._dev_fallback_api_key(account.provider)
                if fallback_key:
                    return ProviderHealth(
                        account=account,
                        is_healthy=True,
                        reason="Development fallback credentials available",
                    )
            return ProviderHealth(account=account, is_healthy=False, reason="Missing API key")

        return ProviderHealth(account=account, is_healthy=True, reason="Credentials present")

    def _dev_fallback_api_key(self, provider: str) -> str | None:
        if provider == "anthropic":
            return self.settings.anthropic_api_key
        if provider == "openai":
            return self.settings.openai_api_key
        if provider == "gemini":
            return self.settings.gemini_api_key
        if provider == "groq":
            return self.settings.groq_api_key
        return None

    async def _load_monthly_usage(self, workspace_id: UUID) -> dict[str, Decimal]:
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(
                AIRequest.selected_account_id,
                func.coalesce(func.sum(AIRequest.estimated_cost), 0),
            )
            .join(Conversation, Conversation.id == AIRequest.conversation_id)
            .where(
                Conversation.workspace_id == workspace_id,
                AIRequest.selected_account_id.is_not(None),
                AIRequest.status == AIRequestStatus.COMPLETED,
                AIRequest.completed_at >= month_start,
            )
            .group_by(AIRequest.selected_account_id)
        )
        return {
            str(account_id): Decimal(str(total))
            for account_id, total in result.all()
            if account_id is not None
        }

    def _fallback_decision(
        self,
        context: RoutingContext,
        policy_type: RoutingPolicyType,
        reason: str,
    ) -> RoutingDecision:
        provider_name = context.provider or self.settings.ai_provider
        model_name = context.model or self.ai_account_service.resolve_model(provider_name, None)
        return RoutingDecision(
            selected_account=None,
            selected_model=model_name,
            policy_used=policy_type,
            score=None,
            decision_reason=f"{reason}; using environment fallback ({provider_name})",
            credentials=None,
        )
