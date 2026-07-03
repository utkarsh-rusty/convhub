from __future__ import annotations

from contextvars import Token
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.demo.context import DemoRuntimeContext, reset_demo_runtime, set_demo_runtime
from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)
from app.models.workspace_demo_settings import WorkspaceDemoSettings


async def bind_workspace_demo_context(
    db: AsyncSession,
    workspace_id: UUID,
) -> Token | None:
    settings = get_settings()
    if not settings.enable_demo_mode:
        return None

    result = await db.execute(
        select(WorkspaceDemoSettings).where(
            WorkspaceDemoSettings.workspace_id == workspace_id,
        )
    )
    demo_settings = result.scalar_one_or_none()

    if demo_settings is None:
        runtime = DemoRuntimeContext(
            workspace_id=workspace_id,
            pricing_profile=PricingProfileType.PRODUCTION,
            provider_simulation=ProviderSimulationMode.NORMAL,
            routing_override_mode=RoutingOverrideMode.NORMAL,
            routing_override_account_id=None,
        )
    else:
        runtime = DemoRuntimeContext(
            workspace_id=workspace_id,
            pricing_profile=demo_settings.pricing_profile,
            provider_simulation=demo_settings.provider_simulation,
            routing_override_mode=demo_settings.routing_override_mode,
            routing_override_account_id=demo_settings.routing_override_account_id,
        )

    return set_demo_runtime(runtime)


def reset_demo_context(token: Token | None) -> None:
    reset_demo_runtime(token)
