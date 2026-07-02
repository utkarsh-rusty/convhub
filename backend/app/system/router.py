from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_accounts.deps import get_ai_account_service, require_workspace_admin
from app.ai_accounts.service import AIAccountService
from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext
from app.core.config import Settings, get_settings
from app.realtime.manager import get_ws_manager
from app.resource_management.budget_service import BudgetService
from app.system.schemas import ComponentStatus, ProviderHealthRow, SystemStatusResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("", response_model=SystemStatusResponse)
async def get_system_status(
    ctx: WorkspaceContext = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_db),
    ai_account_service: AIAccountService = Depends(get_ai_account_service),
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    components: list[ComponentStatus] = []

    try:
        await db.execute(text("SELECT 1"))
        components.append(
            ComponentStatus(name="Database", status="healthy", detail="PostgreSQL reachable"),
        )
    except Exception as exc:
        components.append(
            ComponentStatus(
                name="Database",
                status="unhealthy",
                detail=str(exc)[:200],
            ),
        )

    manager = get_ws_manager()
    ws_active = manager.is_active
    components.append(
        ComponentStatus(
            name="WebSocket",
            status="healthy" if ws_active else "degraded",
            detail=f"{manager.connection_count()} active connection(s)",
        ),
    )

    budget_service = BudgetService(db=db)
    try:
        budget_settings = await budget_service.get_workspace_budget_settings(ctx.workspace_id)
        borrow_detail = (
            "Borrowing enabled"
            if budget_settings.allow_credit_borrowing
            else "Borrowing disabled"
        )
        components.append(
            ComponentStatus(
                name="Credit Engine",
                status="healthy",
                detail=f"Policy: {budget_settings.routing_policy.value}",
            ),
        )
        components.append(
            ComponentStatus(
                name="Borrow Engine",
                status="healthy",
                detail=borrow_detail,
            ),
        )
    except Exception as exc:
        components.append(
            ComponentStatus(
                name="Credit Engine",
                status="unhealthy",
                detail=str(exc)[:200],
            ),
        )
        components.append(
            ComponentStatus(name="Borrow Engine", status="unhealthy", detail="Unavailable"),
        )

    accounts = await ai_account_service.list_accounts(ctx)
    active_accounts = [account for account in accounts if account.is_active]
    components.append(
        ComponentStatus(
            name="Routing Engine",
            status="healthy" if active_accounts else "degraded",
            detail=f"{len(active_accounts)} active provider account(s)",
        ),
    )

    providers = [
        ProviderHealthRow(
            account_id=account.id,
            provider=account.provider,
            model=ai_account_service.resolve_model(account.provider, account),
            display_name=account.display_name,
            owner_name=account.owner_name,
            healthy=account.is_active,
            last_used_at=account.last_used_at,
            request_count=account.request_count,
            credits_used=account.credits_used,
        )
        for account in accounts
    ]

    return SystemStatusResponse(
        environment=settings.app_env,
        demo_mode=settings.enable_demo_mode,
        components=components,
        providers=providers,
    )
