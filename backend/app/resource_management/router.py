from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import WorkspaceRole
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_management.transaction_labels import format_credit_transaction_display
from app.resource_management.schemas import (
    BudgetResponse,
    CreditTransactionListResponse,
    CreditTransactionResponse,
    WorkspaceBudgetSettingsResponse,
    WorkspaceBudgetSettingsUpdate,
)
from app.workspaces.deps import get_workspace_membership, require_workspace_roles

router = APIRouter(prefix="/workspaces", tags=["credits"])


def get_budget_service(db: AsyncSession = Depends(get_db)) -> BudgetService:
    return BudgetService(db=db)


@router.get("/{workspace_id}/budget/me", response_model=BudgetResponse)
async def get_my_budget(
    workspace_id: UUID,
    membership: WorkspaceMember = Depends(get_workspace_membership),
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponse:
    budget = await service.reset_if_needed(workspace_id, membership.user_id)
    return BudgetResponse.model_validate(budget)


@router.get("/{workspace_id}/credits/history", response_model=CreditTransactionListResponse)
async def list_my_credit_history(
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(get_workspace_membership),
    service: BudgetService = Depends(get_budget_service),
) -> CreditTransactionListResponse:
    transactions, total = await service.list_transactions(
        workspace_id,
        membership.user_id,
        limit=limit,
        offset=offset,
    )
    return CreditTransactionListResponse(
        items=[
            CreditTransactionResponse(
                id=item.id,
                workspace_id=item.workspace_id,
                request_id=item.request_id,
                from_user_id=item.from_user_id,
                to_user_id=item.to_user_id,
                transaction_type=item.transaction_type,
                amount=item.amount,
                description=item.description,
                display_description=format_credit_transaction_display(
                    item,
                    membership.user_id,
                ),
                created_at=item.created_at,
            )
            for item in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{workspace_id}/settings/budget",
    response_model=WorkspaceBudgetSettingsResponse,
)
async def get_workspace_budget_settings(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    service: BudgetService = Depends(get_budget_service),
) -> WorkspaceBudgetSettingsResponse:
    settings = await service.get_workspace_budget_settings(workspace_id)
    return WorkspaceBudgetSettingsResponse.model_validate(settings)


@router.patch(
    "/{workspace_id}/settings/budget",
    response_model=WorkspaceBudgetSettingsResponse,
)
async def update_workspace_budget_settings(
    workspace_id: UUID,
    data: WorkspaceBudgetSettingsUpdate,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    service: BudgetService = Depends(get_budget_service),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceBudgetSettingsResponse:
    settings = await service.update_workspace_budget_settings(
        workspace_id,
        monthly_default_credits=data.monthly_default_credits,
        allow_credit_borrowing=data.allow_credit_borrowing,
        allow_emergency_pool=data.allow_emergency_pool,
        allow_local_models=data.allow_local_models,
        hard_budget_enforcement=data.hard_budget_enforcement,
        routing_policy=data.routing_policy,
    )
    await db.commit()
    await db.refresh(settings)
    return WorkspaceBudgetSettingsResponse.model_validate(settings)
