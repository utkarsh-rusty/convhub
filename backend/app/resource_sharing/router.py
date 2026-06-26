from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import WorkspaceRole
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_sharing.preference_service import LendingPreferenceService
from app.resource_sharing.schemas import (
    LendingPreferenceResponse,
    LendingPreferenceUpdate,
    WorkspaceSharingMemberResponse,
    WorkspaceSharingOverviewResponse,
)
from app.workspaces.deps import get_workspace_membership, require_workspace_roles

router = APIRouter(prefix="/workspaces", tags=["resource-sharing"])


def get_budget_service(db: AsyncSession = Depends(get_db)) -> BudgetService:
    return BudgetService(db=db)


def get_lending_preference_service(db: AsyncSession = Depends(get_db)) -> LendingPreferenceService:
    return LendingPreferenceService(db=db)


@router.get("/{workspace_id}/sharing/me", response_model=LendingPreferenceResponse)
async def get_my_sharing_preferences(
    workspace_id: UUID,
    membership: WorkspaceMember = Depends(get_workspace_membership),
    service: LendingPreferenceService = Depends(get_lending_preference_service),
) -> LendingPreferenceResponse:
    preference = await service.get_my_preference(workspace_id, membership.user_id)
    return LendingPreferenceResponse.model_validate(preference)


@router.patch("/{workspace_id}/sharing/me", response_model=LendingPreferenceResponse)
async def update_my_sharing_preferences(
    workspace_id: UUID,
    data: LendingPreferenceUpdate,
    membership: WorkspaceMember = Depends(get_workspace_membership),
    service: LendingPreferenceService = Depends(get_lending_preference_service),
    db: AsyncSession = Depends(get_db),
) -> LendingPreferenceResponse:
    preference = await service.update_my_preference(
        workspace_id,
        membership.user_id,
        auto_share_enabled=data.auto_share_enabled,
        monthly_share_limit=data.monthly_share_limit,
        minimum_reserved_credits=data.minimum_reserved_credits,
        priority=data.priority,
    )
    await db.commit()
    await db.refresh(preference)
    return LendingPreferenceResponse.model_validate(preference)


@router.get("/{workspace_id}/sharing", response_model=WorkspaceSharingOverviewResponse)
async def get_workspace_sharing_overview(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    service: LendingPreferenceService = Depends(get_lending_preference_service),
    budget_service: BudgetService = Depends(get_budget_service),
) -> WorkspaceSharingOverviewResponse:
    rows = await service.list_workspace_sharing(workspace_id, budget_service)
    return WorkspaceSharingOverviewResponse(
        members=[WorkspaceSharingMemberResponse.model_validate(row) for row in rows],
    )
