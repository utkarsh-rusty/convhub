from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import ChatMessage
from app.ai.providers.factory import create_provider
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
        encrypted_credentials = self.encryption.encrypt({"api_key": data.api_key})

        account = AIAccount(
            workspace_id=ctx.workspace_id,
            provider=data.provider,
            display_name=data.display_name,
            encrypted_credentials=encrypted_credentials,
            is_active=data.is_active,
            monthly_budget=data.monthly_budget,
            priority=data.priority,
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
            credentials = self.encryption.decrypt(account.encrypted_credentials)
            provider = create_provider(
                provider_name=account.provider,
                model=self.settings.ai_model,
                credentials=credentials,
                settings=self.settings,
                allow_dev_fallback=False,
            )
            await provider.generate(
                messages=[ChatMessage(role="user", content="Reply with the word OK.")],
                system_prompt=None,
            )
        except Exception as exc:
            return AIAccountTestResponse(success=False, message=str(exc))

        return AIAccountTestResponse(success=True, message="Connection successful")

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
        try:
            return self.encryption.decrypt(account.encrypted_credentials)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored AI account credentials are invalid",
            ) from exc
