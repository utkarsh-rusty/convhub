from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_accounts.deps import get_ai_account_service
from app.ai_accounts.service import AIAccountService
from app.api.deps import get_db
from app.auth.deps import get_current_user
from app.conversations.deps import WorkspaceContext
from app.models.conversation import Conversation
from app.models.enums import RoutingPolicyType, WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.routing.context import RoutingContext
from app.routing.decision import RoutingDecision
from app.routing.deps import get_budget_service, get_routing_engine
from app.routing.engine import RoutingEngine
from app.routing.schemas import (
    RoutingAccountSummary,
    RoutingPreview,
    RoutingSettingsResponse,
    RoutingSettingsUpdate,
)
from app.workspaces.deps import get_workspace_membership, require_workspace_roles

router = APIRouter(prefix="/workspaces", tags=["routing"])


async def _load_workspace(db: AsyncSession, workspace_id: UUID) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def _build_preview(decision: RoutingDecision, routing_policy: RoutingPolicyType) -> RoutingPreview:
    if decision.selected_account is not None:
        provider = decision.selected_account.provider
    else:
        provider = decision.selected_model.split("-")[0] if decision.selected_model else "env"
    return RoutingPreview(
        selected_account_id=(decision.selected_account.id if decision.selected_account else None),
        selected_provider=provider,
        selected_model=decision.selected_model,
        policy_used=decision.policy_used,
        routing_policy=routing_policy,
        score=decision.score,
        decision_reason=decision.decision_reason,
    )


async def _routing_response(
    *,
    db: AsyncSession,
    ctx: WorkspaceContext,
    engine: RoutingEngine,
    ai_account_service: AIAccountService,
    budget_service: BudgetService,
) -> RoutingSettingsResponse:
    settings = await budget_service.get_workspace_budget_settings(ctx.workspace_id)
    workspace = await _load_workspace(db, ctx.workspace_id)
    accounts = await ai_account_service.list_accounts(ctx)

    preview_context = RoutingContext(
        workspace=workspace,
        requesting_user=ctx.user,
        conversation=Conversation(
            workspace_id=ctx.workspace_id,
            owner_id=ctx.user.id,
            title="Routing Preview",
        ),
        provider=None,
        model=None,
        estimated_cost=Decimal("0"),
        participant_user_ids=frozenset({ctx.user.id}),
    )
    decision = await engine.preview(preview_context)

    return RoutingSettingsResponse(
        routing_policy=settings.routing_policy,
        active_accounts=[
            RoutingAccountSummary.model_validate(account)
            for account in accounts
            if account.is_active
        ],
        preview=_build_preview(decision, settings.routing_policy),
    )


@router.get("/{workspace_id}/routing", response_model=RoutingSettingsResponse)
async def get_routing_settings(
    workspace_id: UUID,
    membership: WorkspaceMember = Depends(get_workspace_membership),
    current_user: User = Depends(get_current_user),
    engine: RoutingEngine = Depends(get_routing_engine),
    ai_account_service: AIAccountService = Depends(get_ai_account_service),
    budget_service: BudgetService = Depends(get_budget_service),
    db: AsyncSession = Depends(get_db),
) -> RoutingSettingsResponse:
    ctx = WorkspaceContext(workspace_id=workspace_id, user=current_user, membership=membership)
    return await _routing_response(
        db=db,
        ctx=ctx,
        engine=engine,
        ai_account_service=ai_account_service,
        budget_service=budget_service,
    )


@router.patch("/{workspace_id}/routing", response_model=RoutingSettingsResponse)
async def update_routing_settings(
    workspace_id: UUID,
    data: RoutingSettingsUpdate,
    membership: WorkspaceMember = Depends(
        require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    ),
    current_user: User = Depends(get_current_user),
    engine: RoutingEngine = Depends(get_routing_engine),
    ai_account_service: AIAccountService = Depends(get_ai_account_service),
    budget_service: BudgetService = Depends(get_budget_service),
    db: AsyncSession = Depends(get_db),
) -> RoutingSettingsResponse:
    await budget_service.update_workspace_budget_settings(
        workspace_id,
        routing_policy=data.routing_policy,
    )
    await db.commit()
    ctx = WorkspaceContext(workspace_id=workspace_id, user=current_user, membership=membership)
    return await _routing_response(
        db=db,
        ctx=ctx,
        engine=engine,
        ai_account_service=ai_account_service,
        budget_service=budget_service,
    )
