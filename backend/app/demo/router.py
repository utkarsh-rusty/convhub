from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.router import get_auth_service
from app.auth.schemas import LoginRequest
from app.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.demo.constants import DEMO_PASSWORD, DEMO_PERSONAS, DEMO_WORKSPACE_SLUG
from app.demo.deps import get_demo_service, require_demo_mode
from app.demo.schemas import (
    DemoActionResponse,
    DemoConfigResponse,
    DemoEventResponse,
    DemoEventsResponse,
    DemoLoginRequest,
    DemoLoginResponse,
    DemoSettingsResponse,
    DemoUserResponse,
    DemoUsersResponse,
    PricingProfileUpdate,
    ProviderSimulationUpdate,
    RoutingOverrideUpdate,
    SetUserCreditsRequest,
    UserBudgetSummary,
    UserCreditsResponse,
)
from app.demo.service import DemoService
from app.models.enums import WorkspaceRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.workspaces.deps import require_workspace_roles

router = APIRouter(tags=["demo"])
workspace_router = APIRouter(prefix="/workspaces", tags=["demo"])


@router.get("/demo/config", response_model=DemoConfigResponse)
async def get_demo_config(
    settings: Settings = Depends(get_settings),
) -> DemoConfigResponse:
    return DemoConfigResponse(enabled=settings.enable_demo_mode)


@router.get("/demo/users", response_model=DemoUsersResponse)
async def list_demo_users(
    _: Settings = Depends(require_demo_mode),
) -> DemoUsersResponse:
    return DemoUsersResponse(
        workspace_slug=DEMO_WORKSPACE_SLUG,
        users=[
            DemoUserResponse(
                persona=persona,
                name=details["name"],
                email=details["email"],
                role=details["role"],
            )
            for persona, details in DEMO_PERSONAS.items()
        ],
    )


@router.post("/demo/login", response_model=DemoLoginResponse)
async def demo_login(
    data: DemoLoginRequest,
    _: Settings = Depends(require_demo_mode),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
) -> DemoLoginResponse:
    persona = DEMO_PERSONAS[data.persona]
    tokens = await auth_service.login(
        LoginRequest.model_construct(
            email=persona["email"],
            password=DEMO_PASSWORD,
        ),
    )

    workspace_id: UUID | None = None
    result = await db.execute(select(Workspace).where(Workspace.slug == DEMO_WORKSPACE_SLUG))
    workspace = result.scalar_one_or_none()
    if workspace is not None:
        workspace_id = workspace.id

    return DemoLoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        workspace_id=workspace_id,
        workspace_slug=DEMO_WORKSPACE_SLUG if workspace_id else None,
    )


@workspace_router.get("/{workspace_id}/demo", response_model=DemoSettingsResponse)
async def get_demo_settings(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
) -> DemoSettingsResponse:
    settings_row = await service.get_settings(workspace_id)
    return DemoSettingsResponse.model_validate(settings_row)


@workspace_router.patch("/{workspace_id}/demo/pricing-profile", response_model=DemoSettingsResponse)
async def update_pricing_profile(
    workspace_id: UUID,
    data: PricingProfileUpdate,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoSettingsResponse:
    settings_row = await service.update_pricing_profile(workspace_id, data.pricing_profile)
    await db.commit()
    return DemoSettingsResponse.model_validate(settings_row)


@workspace_router.patch(
    "/{workspace_id}/demo/provider-simulation", response_model=DemoSettingsResponse
)
async def update_provider_simulation(
    workspace_id: UUID,
    data: ProviderSimulationUpdate,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoSettingsResponse:
    settings_row = await service.update_provider_simulation(
        workspace_id,
        data.provider_simulation,
    )
    await db.commit()
    return DemoSettingsResponse.model_validate(settings_row)


@workspace_router.patch(
    "/{workspace_id}/demo/routing-override", response_model=DemoSettingsResponse
)
async def update_routing_override(
    workspace_id: UUID,
    data: RoutingOverrideUpdate,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoSettingsResponse:
    settings_row = await service.update_routing_override(
        workspace_id,
        data.routing_override_mode,
        data.routing_override_account_id,
    )
    await db.commit()
    return DemoSettingsResponse.model_validate(settings_row)


@workspace_router.get("/{workspace_id}/demo/budgets", response_model=list[UserBudgetSummary])
async def list_demo_budgets(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
) -> list[UserBudgetSummary]:
    budgets = await service.list_member_budgets(workspace_id)
    return [UserBudgetSummary.model_validate(budget) for budget in budgets]


@workspace_router.post("/{workspace_id}/demo/credits/set", response_model=UserCreditsResponse)
async def set_user_credits(
    workspace_id: UUID,
    data: SetUserCreditsRequest,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> UserCreditsResponse:
    budget = await service.set_user_remaining_credits(
        workspace_id,
        data.user_id,
        data.remaining_credits,
    )
    await db.commit()
    return UserCreditsResponse(budget=UserBudgetSummary.model_validate(budget))


@workspace_router.post(
    "/{workspace_id}/demo/credits/reset-user", response_model=UserCreditsResponse
)
async def reset_user_credits(
    workspace_id: UUID,
    user_id: UUID = Query(...),
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> UserCreditsResponse:
    budget = await service.reset_user_credits(workspace_id, user_id)
    await db.commit()
    return UserCreditsResponse(budget=UserBudgetSummary.model_validate(budget))


@workspace_router.post("/{workspace_id}/demo/credits/reset-all", response_model=DemoActionResponse)
async def reset_all_credits(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoActionResponse:
    count = await service.reset_all_workspace_credits(workspace_id)
    await db.commit()
    return DemoActionResponse(
        message="Reset all workspace member credits to monthly allocation",
        affected_count=count,
    )


@workspace_router.post("/{workspace_id}/demo/ledger/clear", response_model=DemoActionResponse)
async def clear_ledger(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoActionResponse:
    count = await service.clear_ledger_history(workspace_id)
    await db.commit()
    return DemoActionResponse(
        message="Cleared workspace ledger history",
        affected_count=count,
    )


@workspace_router.post("/{workspace_id}/demo/reseed", response_model=DemoActionResponse)
async def reseed_allocations(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
    db: AsyncSession = Depends(get_db),
) -> DemoActionResponse:
    count = await service.reseed_demo_allocations(workspace_id)
    await db.commit()
    return DemoActionResponse(
        message="Reseeded demo credit allocations",
        affected_count=count,
    )


@workspace_router.get("/{workspace_id}/demo/events", response_model=DemoEventsResponse)
async def list_demo_events(
    workspace_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    __: Settings = Depends(require_demo_mode),
    service: DemoService = Depends(get_demo_service),
) -> DemoEventsResponse:
    events = await service.list_recent_events(workspace_id, limit=limit)
    return DemoEventsResponse(
        items=[DemoEventResponse.model_validate(event) for event in events],
    )
