from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_accounts.service import AIAccountService
from app.core.config import Settings
from app.core.credentials import CredentialEncryption
from app.demo.runtime import NoOpRoutingOverride, RoutingOverrideProvider
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.enums import AIRequestStatus, RoutingPolicyType
from app.models.workspace_budget_settings import WorkspaceBudgetSettings
from app.resource_management.budget_service import BudgetService
from app.routing.context import RoutingContext
from app.routing.decision import RoutingDecision, RoutingScore
from app.routing.health import ProviderHealth
from app.routing.policy import FREE_PROVIDERS, get_policy


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

    @staticmethod
    def get_policy(policy_type: RoutingPolicyType):
        return get_policy(policy_type)

    async def select(self, context: RoutingContext) -> RoutingDecision:
        from app.routing.orchestrator import AccountRoutingOrchestrator

        orchestrator = AccountRoutingOrchestrator(self)
        return await orchestrator.select(context)

    async def preview(self, context: RoutingContext) -> RoutingDecision:
        return await self.select(context)

    async def load_user_accounts(self, workspace_id: UUID, owner_user_id: UUID) -> list[AIAccount]:
        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == workspace_id,
                AIAccount.is_active.is_(True),
                AIAccount.owner_user_id == owner_user_id,
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        return list(result.scalars().all())

    async def select_for_owner(
        self, context: RoutingContext, owner_user_id: UUID
    ) -> RoutingDecision:
        from app.routing.orchestrator import AccountRoutingOrchestrator

        scoped = RoutingContext(
            workspace=context.workspace,
            requesting_user=context.requesting_user,
            conversation=context.conversation,
            provider=context.provider,
            model=context.model,
            estimated_cost=context.estimated_cost,
            participant_user_ids=context.participant_user_ids,
            scoped_owner_id=owner_user_id,
            prompt_context=context.prompt_context,
        )
        orchestrator = AccountRoutingOrchestrator(self)
        return await orchestrator.select(scoped)

    async def load_participant_accounts(self, context: RoutingContext) -> list[AIAccount]:
        if not context.participant_user_ids:
            return []

        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == context.workspace.id,
                AIAccount.is_active.is_(True),
                AIAccount.owner_user_id.in_(context.participant_user_ids),
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        return list(result.scalars().all())

    def filter_healthy_accounts(
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

    async def build_decision(
        self,
        scored: RoutingScore,
        *,
        policy_type: RoutingPolicyType,
        decision_reason: str,
    ) -> RoutingDecision:
        account = scored.account
        model = self.ai_account_service.resolve_model(account.provider, account)
        credentials = await self.ai_account_service.get_decrypted_credentials(account)
        return RoutingDecision(
            selected_account=account,
            selected_model=model,
            policy_used=policy_type,
            score=scored.score,
            decision_reason=decision_reason,
            credentials=credentials,
        )

    def fallback_decision(
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

    def _check_credentials(self, account: AIAccount) -> ProviderHealth:
        if account.provider in FREE_PROVIDERS:
            return ProviderHealth(
                account=account, is_healthy=True, reason="No credentials required"
            )

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

    async def load_monthly_usage(self, workspace_id: UUID) -> dict[str, Decimal]:
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
