from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_accounts.deps import get_ai_account_service, get_credential_encryption
from app.ai_accounts.service import AIAccountService
from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialEncryption
from app.demo.runtime import DemoRoutingOverride, NoOpRoutingOverride
from app.resource_management.budget_service import BudgetService
from app.routing.engine import RoutingEngine


def get_budget_service(db: AsyncSession = Depends(get_db)) -> BudgetService:
    return BudgetService(db=db)


def get_routing_engine(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    encryption: CredentialEncryption = Depends(get_credential_encryption),
    ai_account_service: AIAccountService = Depends(get_ai_account_service),
    budget_service: BudgetService = Depends(get_budget_service),
) -> RoutingEngine:
    routing_override = NoOpRoutingOverride()
    if settings.enable_demo_mode:
        routing_override = DemoRoutingOverride(ai_account_service)

    return RoutingEngine(
        db=db,
        settings=settings,
        encryption=encryption,
        ai_account_service=ai_account_service,
        budget_service=budget_service,
        routing_override=routing_override,
    )
