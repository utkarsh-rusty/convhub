from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai_accounts.service import AIAccountService
from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialEncryption
from app.models.ai_account import AIAccount
from app.models.enums import WorkspaceRole


def get_credential_encryption(settings: Settings = Depends(get_settings)) -> CredentialEncryption:
    return CredentialEncryption(settings.credentials_encryption_key)


def get_ai_account_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    encryption: CredentialEncryption = Depends(get_credential_encryption),
) -> AIAccountService:
    return AIAccountService(db=db, settings=settings, encryption=encryption)


def require_workspace_admin(ctx: WorkspaceContext = Depends(get_workspace_context)) -> WorkspaceContext:
    if ctx.membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient workspace permissions",
        )
    return ctx


def can_manage_account(ctx: WorkspaceContext, account: AIAccount) -> bool:
    if account.owner_user_id == ctx.user.id:
        return True
    return ctx.membership.role in {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}


async def get_ai_account(
    account_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> AIAccount:
    result = await db.execute(
        select(AIAccount)
        .options(selectinload(AIAccount.owner))
        .where(
            AIAccount.id == account_id,
            AIAccount.workspace_id == ctx.workspace_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI account not found",
        )
    return account


def require_account_manager(
    account: AIAccount = Depends(get_ai_account),
    ctx: WorkspaceContext = Depends(get_workspace_context),
) -> AIAccount:
    if not can_manage_account(ctx, account):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage this AI account",
        )
    return account
