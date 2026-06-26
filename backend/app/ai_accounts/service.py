from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt_builder import PromptBuilder, PromptContext
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
        await self.db.refresh(account)
        return AIAccountResponse.model_validate(account)

    async def list_accounts(self, workspace_id: UUID) -> list[AIAccountResponse]:
        result = await self.db.execute(
            select(AIAccount)
            .where(AIAccount.workspace_id == workspace_id)
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
        )
        return [AIAccountResponse.model_validate(account) for account in result.scalars().all()]

    async def update_account(
        self,
        account: AIAccount,
        data: AIAccountUpdate,
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
        await self.db.refresh(account)
        return AIAccountResponse.model_validate(account)

    async def delete_account(self, account: AIAccount) -> None:
        await self.db.delete(account)
        await self.db.commit()

    async def test_account(self, account: AIAccount) -> AIAccountTestResponse:
        try:
            credentials = (
                None if account.provider == "ollama" else self.encryption.decrypt(account.encrypted_credentials)
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
        if provider_name == "mock":
            return "mock"
        return self.settings.ai_model

    async def resolve_primary_active_account(
        self,
        workspace_id: UUID,
    ) -> AIAccount | None:
        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == workspace_id,
                AIAccount.is_active.is_(True),
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def resolve_active_account(
        self,
        workspace_id: UUID,
        provider_name: str,
    ) -> AIAccount | None:
        result = await self.db.execute(
            select(AIAccount)
            .where(
                AIAccount.workspace_id == workspace_id,
                AIAccount.provider == provider_name,
                AIAccount.is_active.is_(True),
            )
            .order_by(AIAccount.priority.asc(), AIAccount.created_at.asc())
            .limit(1)
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
