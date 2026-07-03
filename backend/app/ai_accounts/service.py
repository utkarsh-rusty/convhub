from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import ChatMessage
from app.ai.providers.factory import create_provider
from app.ai.providers.ollama import OllamaProvider
from app.ai_accounts.schemas import (
    AIAccountCreate,
    AIAccountResponse,
    AIAccountTestResponse,
    AIAccountUpdate,
)
from app.conversations.deps import WorkspaceContext
from app.core.config import Settings
from app.core.credentials import CredentialEncryption
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.enums import AIRequestStatus


class AIAccountService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        encryption: CredentialEncryption,
    ) -> None:
        self.db = db
        self.settings = settings
        self.encryption = encryption

    async def create_account(
        self,
        ctx: WorkspaceContext,
        data: AIAccountCreate,
    ) -> AIAccountResponse:
        api_key = data.api_key or ""
        encrypted_credentials = self.encryption.encrypt({"api_key": api_key})

        account = AIAccount(
            workspace_id=ctx.workspace_id,
            owner_user_id=ctx.user.id,
            provider=data.provider,
            display_name=data.display_name,
            encrypted_credentials=encrypted_credentials,
            is_active=data.is_active,
            monthly_budget=data.monthly_budget,
            priority=data.priority,
            default_model=data.default_model,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account, attribute_names=["owner"])
        return self._to_response(account, ctx.user.id)

    async def list_accounts(self, ctx: WorkspaceContext) -> list[AIAccountResponse]:
        result = await self.db.execute(
            select(AIAccount)
            .options(selectinload(AIAccount.owner))
            .where(AIAccount.workspace_id == ctx.workspace_id)
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        accounts = list(result.scalars().all())
        stats = await self._load_account_stats([account.id for account in accounts])
        return [
            self._to_response(account, ctx.user.id, stats.get(account.id)) for account in accounts
        ]

    async def _load_account_stats(
        self,
        account_ids: list[UUID],
    ) -> dict[UUID, dict]:
        if not account_ids:
            return {}

        result = await self.db.execute(
            select(
                AIRequest.selected_account_id,
                func.count(AIRequest.id),
                func.max(AIRequest.completed_at),
                func.coalesce(func.sum(AIRequest.estimated_cost), 0),
            )
            .where(
                AIRequest.selected_account_id.in_(account_ids),
                AIRequest.status == AIRequestStatus.COMPLETED,
            )
            .group_by(AIRequest.selected_account_id)
        )

        return {
            account_id: {
                "request_count": int(count),
                "last_used_at": last_used,
                "credits_used": credits,
            }
            for account_id, count, last_used, credits in result.all()
            if account_id is not None
        }

    def _to_response(
        self,
        account: AIAccount,
        current_user_id: UUID,
        stats: dict | None = None,
    ) -> AIAccountResponse:
        base = AIAccountResponse.model_validate(account).model_copy(
            update={
                "owner_name": account.owner.name if account.owner is not None else None,
                "is_mine": account.owner_user_id == current_user_id,
            }
        )
        if not stats:
            return base
        return base.model_copy(
            update={
                "request_count": stats["request_count"],
                "last_used_at": stats["last_used_at"],
                "credits_used": stats["credits_used"],
            }
        )

    async def update_account(
        self,
        account: AIAccount,
        data: AIAccountUpdate,
        *,
        current_user_id: UUID,
    ) -> AIAccountResponse:
        if data.display_name is not None:
            account.display_name = data.display_name
        if data.is_active is not None:
            account.is_active = data.is_active
        if data.monthly_budget is not None:
            account.monthly_budget = data.monthly_budget
        if data.priority is not None:
            account.priority = data.priority
        if data.default_model is not None:
            account.default_model = data.default_model or None
        if data.api_key is not None:
            account.encrypted_credentials = self.encryption.encrypt({"api_key": data.api_key})

        await self.db.commit()
        result = await self.db.execute(
            select(AIAccount)
            .options(selectinload(AIAccount.owner))
            .where(AIAccount.id == account.id)
        )
        refreshed = result.scalar_one()
        return self._to_response(refreshed, current_user_id)

    async def delete_account(self, account: AIAccount) -> None:
        await self.db.delete(account)
        await self.db.commit()

    async def test_account(self, account: AIAccount) -> AIAccountTestResponse:
        try:
            credentials = (
                None
                if account.provider == "ollama"
                else self.encryption.decrypt(account.encrypted_credentials)
            )
            model = self.resolve_model(account.provider, account)
            provider = create_provider(
                provider_name=account.provider,
                credentials=credentials,
                settings=self.settings,
                allow_dev_fallback=False,
            )
            if isinstance(provider, OllamaProvider):
                await provider.test_connection()
            else:
                test_context = PromptContext(
                    system_prompt="",
                    chat_messages=[ChatMessage(role="user", content="Reply with the word OK.")],
                    metadata={},
                )
                await provider.generate(test_context, model)
        except Exception as exc:
            return AIAccountTestResponse(success=False, message=str(exc))

        return AIAccountTestResponse(success=True, message="Connection successful")

    def resolve_model(self, provider_name: str, account: AIAccount | None = None) -> str:
        if account is not None and account.default_model:
            return account.default_model
        if provider_name == "ollama":
            return self.settings.ollama_model
        if provider_name == "openai":
            return self.settings.openai_model
        if provider_name == "gemini":
            return self.settings.gemini_model
        if provider_name == "groq":
            return self.settings.groq_model
        if provider_name == "mock":
            return "mock"
        return self.settings.ai_model

    async def resolve_user_accounts(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[AIAccount]:
        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == workspace_id,
                AIAccount.owner_user_id == user_id,
                AIAccount.is_active.is_(True),
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        return list(result.scalars().all())

    async def resolve_primary_active_account(
        self,
        workspace_id: UUID,
        *,
        owner_user_id: UUID | None = None,
        participant_user_ids: frozenset[UUID] | None = None,
    ) -> AIAccount | None:
        query = select(AIAccount).where(
            AIAccount.workspace_id == workspace_id,
            AIAccount.is_active.is_(True),
        )
        if owner_user_id is not None:
            query = query.where(AIAccount.owner_user_id == owner_user_id)
        if participant_user_ids is not None:
            query = query.where(AIAccount.owner_user_id.in_(participant_user_ids))
        result = await self.db.execute(
            query.order_by(AIAccount.priority.asc(), AIAccount.created_at.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def resolve_active_account(
        self,
        workspace_id: UUID,
        provider_name: str,
        *,
        owner_user_id: UUID | None = None,
        participant_user_ids: frozenset[UUID] | None = None,
    ) -> AIAccount | None:
        query = select(AIAccount).where(
            AIAccount.workspace_id == workspace_id,
            AIAccount.provider == provider_name,
            AIAccount.is_active.is_(True),
        )
        if owner_user_id is not None:
            query = query.where(AIAccount.owner_user_id == owner_user_id)
        if participant_user_ids is not None:
            query = query.where(AIAccount.owner_user_id.in_(participant_user_ids))
        result = await self.db.execute(
            query.order_by(AIAccount.priority.asc(), AIAccount.created_at.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_decrypted_credentials(self, account: AIAccount) -> dict[str, str]:
        if account.provider == "ollama":
            return {}

        try:
            return self.encryption.decrypt(account.encrypted_credentials)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored AI account credentials are invalid",
            ) from exc
