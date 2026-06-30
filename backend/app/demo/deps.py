from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.resource_management.budget_service import BudgetService
from app.resource_management.pricing_engine import PricingEngine
from app.demo.service import DemoService


def require_demo_mode(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.enable_demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo mode is not enabled",
        )
    return settings


def get_budget_service(db: AsyncSession = Depends(get_db)) -> BudgetService:
    return BudgetService(db=db)


def get_pricing_engine() -> PricingEngine:
    return PricingEngine()


def get_demo_service(
    db: AsyncSession = Depends(get_db),
    budget_service: BudgetService = Depends(get_budget_service),
    settings: Settings = Depends(require_demo_mode),
    pricing_engine: PricingEngine = Depends(get_pricing_engine),
) -> DemoService:
    return DemoService(
        db=db,
        budget_service=budget_service,
        settings=settings,
        pricing_engine=pricing_engine,
    )
