from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.credit_transaction import CreditTransaction
from app.models.demo_event_log import DemoEventLog
from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)
from app.models.user_budget import UserBudget
from app.models.workspace_demo_settings import WorkspaceDemoSettings
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_management.pricing_engine import PricingEngine


class DemoService:
    def __init__(
        self,
        db: AsyncSession,
        budget_service: BudgetService,
        settings: Settings,
        pricing_engine: PricingEngine | None = None,
    ) -> None:
        self.db = db
        self.budget_service = budget_service
        self.settings = settings
        self.pricing_engine = pricing_engine or PricingEngine()

    async def get_or_create_settings(self, workspace_id: UUID) -> WorkspaceDemoSettings:
        result = await self.db.execute(
            select(WorkspaceDemoSettings).where(
                WorkspaceDemoSettings.workspace_id == workspace_id,
            )
        )
        settings = result.scalar_one_or_none()
        if settings is not None:
            return settings

        settings = WorkspaceDemoSettings(workspace_id=workspace_id)
        self.db.add(settings)
        await self.db.flush()
        return settings

    async def get_settings(self, workspace_id: UUID) -> WorkspaceDemoSettings:
        return await self.get_or_create_settings(workspace_id)

    async def update_pricing_profile(
        self,
        workspace_id: UUID,
        profile: PricingProfileType,
    ) -> WorkspaceDemoSettings:
        settings = await self.get_or_create_settings(workspace_id)
        settings.pricing_profile = profile
        await self.db.flush()
        await self._log_event(
            workspace_id,
            "pricing_profile",
            f"Pricing profile set to {profile.value}",
        )
        return settings

    async def update_provider_simulation(
        self,
        workspace_id: UUID,
        mode: ProviderSimulationMode,
    ) -> WorkspaceDemoSettings:
        settings = await self.get_or_create_settings(workspace_id)
        settings.provider_simulation = mode
        await self.db.flush()
        await self._log_event(
            workspace_id,
            "provider_simulation",
            f"Provider simulation set to {mode.value}",
        )
        return settings

    async def update_routing_override(
        self,
        workspace_id: UUID,
        mode: RoutingOverrideMode,
        account_id: UUID | None = None,
    ) -> WorkspaceDemoSettings:
        settings = await self.get_or_create_settings(workspace_id)
        settings.routing_override_mode = mode
        settings.routing_override_account_id = (
            account_id if mode == RoutingOverrideMode.SPECIFIC_ACCOUNT else None
        )
        await self.db.flush()
        await self._log_event(
            workspace_id,
            "routing_override",
            f"Routing override set to {mode.value}",
        )
        return settings

    async def set_user_remaining_credits(
        self,
        workspace_id: UUID,
        user_id: UUID,
        remaining: Decimal,
    ) -> UserBudget:
        if remaining < Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remaining credits cannot be negative",
            )

        budget = await self.budget_service.reset_if_needed(workspace_id, user_id)
        delta = remaining - budget.remaining_credits
        if delta != Decimal("0"):
            await self.budget_service.adjust_credits(
                workspace_id=workspace_id,
                user_id=user_id,
                amount=delta,
                description=f"Demo: set remaining credits to {remaining}",
            )

        await self._log_event(
            workspace_id,
            "credit_adjustment",
            f"Set user {user_id} remaining credits to {remaining}",
        )
        return await self.budget_service.get_budget(workspace_id, user_id)

    async def reset_user_credits(self, workspace_id: UUID, user_id: UUID) -> UserBudget:
        budget = await self.budget_service.allocate_monthly_credits(workspace_id, user_id)
        await self._log_event(
            workspace_id,
            "credit_reset",
            f"Reset user {user_id} to monthly allocation",
        )
        return budget

    async def reset_all_workspace_credits(self, workspace_id: UUID) -> int:
        members = await self._list_member_user_ids(workspace_id)
        for user_id in members:
            await self.budget_service.allocate_monthly_credits(workspace_id, user_id)
        await self._log_event(
            workspace_id,
            "credit_reset_all",
            f"Reset credits for {len(members)} workspace members",
        )
        return len(members)

    async def clear_ledger_history(self, workspace_id: UUID) -> int:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(CreditTransaction)
            .where(CreditTransaction.workspace_id == workspace_id)
        )
        total = int(count_result.scalar_one())
        await self.db.execute(
            delete(CreditTransaction).where(CreditTransaction.workspace_id == workspace_id)
        )
        await self.db.flush()
        await self._log_event(
            workspace_id,
            "clear_ledger",
            f"Cleared {total} ledger transactions",
        )
        return total

    async def reseed_demo_allocations(self, workspace_id: UUID) -> int:
        members = await self._list_member_user_ids(workspace_id)
        for user_id in members:
            await self.budget_service.allocate_monthly_credits(workspace_id, user_id)
        await self._log_event(
            workspace_id,
            "reseed_allocations",
            f"Reseeded demo allocations for {len(members)} members",
        )
        return len(members)

    async def list_recent_events(
        self,
        workspace_id: UUID,
        *,
        limit: int = 20,
    ) -> list[DemoEventLog]:
        result = await self.db.execute(
            select(DemoEventLog)
            .where(DemoEventLog.workspace_id == workspace_id)
            .order_by(DemoEventLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_member_budgets(self, workspace_id: UUID) -> list[UserBudget]:
        result = await self.db.execute(
            select(UserBudget).where(UserBudget.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def _list_member_user_ids(self, workspace_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        return list(result.scalars().all())

    async def _log_event(self, workspace_id: UUID, event_type: str, message: str) -> None:
        self.db.add(
            DemoEventLog(
                workspace_id=workspace_id,
                event_type=event_type,
                message=message,
                created_at=datetime.now(UTC),
            )
        )
        await self.db.flush()
