from fastapi import APIRouter, Depends, status

from app.ai_accounts.deps import (
    get_ai_account_service,
    require_account_manager,
)
from app.ai_accounts.schemas import (
    AIAccountCreate,
    AIAccountResponse,
    AIAccountTestResponse,
    AIAccountUpdate,
)
from app.ai_accounts.service import AIAccountService
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.ai_account import AIAccount

ai_accounts_router = APIRouter(prefix="/ai-accounts", tags=["ai-accounts"])


@ai_accounts_router.post(
    "",
    response_model=AIAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_account(
    data: AIAccountCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: AIAccountService = Depends(get_ai_account_service),
) -> AIAccountResponse:
    return await service.create_account(ctx, data)


@ai_accounts_router.get("", response_model=list[AIAccountResponse])
async def list_ai_accounts(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: AIAccountService = Depends(get_ai_account_service),
) -> list[AIAccountResponse]:
    return await service.list_accounts(ctx)


@ai_accounts_router.patch("/{account_id}", response_model=AIAccountResponse)
async def update_ai_account(
    data: AIAccountUpdate,
    account: AIAccount = Depends(require_account_manager),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: AIAccountService = Depends(get_ai_account_service),
) -> AIAccountResponse:
    return await service.update_account(account, data, current_user_id=ctx.user.id)


@ai_accounts_router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_account(
    account: AIAccount = Depends(require_account_manager),
    service: AIAccountService = Depends(get_ai_account_service),
) -> None:
    await service.delete_account(account)


@ai_accounts_router.post("/{account_id}/test", response_model=AIAccountTestResponse)
async def test_ai_account(
    account: AIAccount = Depends(require_account_manager),
    service: AIAccountService = Depends(get_ai_account_service),
) -> AIAccountTestResponse:
    return await service.test_account(account)
