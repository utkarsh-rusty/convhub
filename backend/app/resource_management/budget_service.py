from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType
from app.models.user_budget import UserBudget
from app.models.workspace_budget_settings import WorkspaceBudgetSettings
from app.models.enums import RoutingPolicyType
from app.resource_management.constants import DEFAULT_MONTHLY_CREDIT_LIMIT
from app.resource_management.exceptions import InsufficientCreditsError


def _next_reset_date(from_day: date | None = None) -> date:
    today = from_day or datetime.now(UTC).date()
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _advance_reset_date(current: date) -> date:
    if current.month == 12:
        return date(current.year + 1, 1, 1)
    return date(current.year, current.month + 1, 1)


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_budget(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        monthly_credit_limit: Decimal | None = None,
    ) -> UserBudget:
        existing = await self._get_budget_row(workspace_id, user_id)
        if existing is not None:
            return existing

        if monthly_credit_limit is None:
            settings_row = await self._get_workspace_budget_settings_row(workspace_id)
            monthly_credit_limit = (
                settings_row.monthly_default_credits
                if settings_row is not None
                else DEFAULT_MONTHLY_CREDIT_LIMIT
            )

        budget = UserBudget(
            workspace_id=workspace_id,
            user_id=user_id,
            monthly_credit_limit=monthly_credit_limit,
            used_credits=Decimal("0"),
            borrowed_credits=Decimal("0"),
            lent_credits=Decimal("0"),
            remaining_credits=monthly_credit_limit,
            reset_date=_next_reset_date(),
        )
        self.db.add(budget)
        await self.db.flush()

        transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=None,
            from_user_id=None,
            to_user_id=user_id,
            transaction_type=CreditTransactionType.ALLOCATION,
            amount=monthly_credit_limit,
            description="Initial monthly credit allocation",
        )
        self.db.add(transaction)
        await self.db.flush()
        return budget

    async def get_budget(self, workspace_id: UUID, user_id: UUID) -> UserBudget:
        budget = await self._get_budget_row(workspace_id, user_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this workspace member",
            )
        return budget

    async def reset_if_needed(self, workspace_id: UUID, user_id: UUID) -> UserBudget:
        budget = await self.get_budget(workspace_id, user_id)
        today = datetime.now(UTC).date()

        while today >= budget.reset_date:
            allocation = budget.monthly_credit_limit
            budget.used_credits = Decimal("0")
            budget.borrowed_credits = Decimal("0")
            budget.lent_credits = Decimal("0")
            budget.remaining_credits = allocation
            budget.reset_date = _advance_reset_date(budget.reset_date)

            transaction = CreditTransaction(
                workspace_id=workspace_id,
                request_id=None,
                from_user_id=None,
                to_user_id=user_id,
                transaction_type=CreditTransactionType.ALLOCATION,
                amount=allocation,
                description="Monthly credit allocation",
            )
            self.db.add(transaction)
            await self.db.flush()

        return budget

    async def has_available_credits(
        self,
        workspace_id: UUID,
        user_id: UUID,
        amount: Decimal,
    ) -> bool:
        if amount <= Decimal("0"):
            return True

        budget = await self.reset_if_needed(workspace_id, user_id)
        return budget.remaining_credits >= amount

    async def consume_credits(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        ai_request_id: UUID,
        amount: Decimal,
        description: str | None = None,
    ) -> CreditTransaction | None:
        if amount <= Decimal("0"):
            return None

        budget = await self.reset_if_needed(workspace_id, user_id)
        if budget.remaining_credits < amount:
            raise InsufficientCreditsError(required=amount, available=budget.remaining_credits)

        transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=ai_request_id,
            from_user_id=user_id,
            to_user_id=None,
            transaction_type=CreditTransactionType.USAGE,
            amount=amount,
            description=description or f"AI request {ai_request_id}",
        )
        self.db.add(transaction)

        budget.used_credits += amount
        budget.remaining_credits -= amount

        await self.db.flush()
        return transaction

    async def allocate_monthly_credits(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> UserBudget:
        budget = await self.get_budget(workspace_id, user_id)
        allocation = budget.monthly_credit_limit

        budget.used_credits = Decimal("0")
        budget.borrowed_credits = Decimal("0")
        budget.lent_credits = Decimal("0")
        budget.remaining_credits = allocation
        budget.reset_date = _next_reset_date()

        transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=None,
            from_user_id=None,
            to_user_id=user_id,
            transaction_type=CreditTransactionType.ALLOCATION,
            amount=allocation,
            description="Monthly credit allocation",
        )
        self.db.add(transaction)
        await self.db.flush()
        return budget

    async def record_usage(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        ai_request_id: UUID,
        amount: Decimal,
    ) -> CreditTransaction | None:
        return await self.consume_credits(
            workspace_id=workspace_id,
            user_id=user_id,
            ai_request_id=ai_request_id,
            amount=amount,
        )

    async def adjust_credits(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        amount: Decimal,
        description: str,
        ai_request_id: UUID | None = None,
    ) -> CreditTransaction | None:
        if amount == Decimal("0"):
            return None

        budget = await self.reset_if_needed(workspace_id, user_id)

        transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=ai_request_id,
            from_user_id=user_id if amount < Decimal("0") else None,
            to_user_id=user_id if amount > Decimal("0") else None,
            transaction_type=CreditTransactionType.ADJUSTMENT,
            amount=abs(amount),
            description=description,
        )
        self.db.add(transaction)

        budget.remaining_credits += amount
        if amount > Decimal("0"):
            budget.used_credits = max(Decimal("0"), budget.used_credits - amount)
        else:
            budget.used_credits += abs(amount)

        await self.db.flush()
        return transaction

    async def list_transactions(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CreditTransaction], int]:
        base_filter = (
            CreditTransaction.workspace_id == workspace_id,
            (CreditTransaction.from_user_id == user_id) | (CreditTransaction.to_user_id == user_id),
        )

        count_result = await self.db.execute(
            select(func.count())
            .select_from(CreditTransaction)
            .where(*base_filter)
        )
        total = int(count_result.scalar_one())

        result = await self.db.execute(
            select(CreditTransaction)
            .where(*base_filter)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_workspace_budget_settings(self, workspace_id: UUID) -> WorkspaceBudgetSettings:
        settings = await self._get_workspace_budget_settings_row(workspace_id)
        if settings is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace budget settings not found",
            )
        return settings

    async def create_workspace_budget_settings(self, workspace_id: UUID) -> WorkspaceBudgetSettings:
        existing = await self._get_workspace_budget_settings_row(workspace_id)
        if existing is not None:
            return existing

        settings = WorkspaceBudgetSettings(
            workspace_id=workspace_id,
            monthly_default_credits=DEFAULT_MONTHLY_CREDIT_LIMIT,
            allow_credit_borrowing=False,
            allow_emergency_pool=False,
            allow_local_models=True,
            routing_policy=RoutingPolicyType.OWNER_FIRST,
        )
        self.db.add(settings)
        await self.db.flush()
        return settings

    async def update_workspace_budget_settings(
        self,
        workspace_id: UUID,
        *,
        monthly_default_credits: Decimal | None = None,
        allow_credit_borrowing: bool | None = None,
        allow_emergency_pool: bool | None = None,
        allow_local_models: bool | None = None,
        routing_policy: RoutingPolicyType | None = None,
    ) -> WorkspaceBudgetSettings:
        settings = await self.get_workspace_budget_settings(workspace_id)

        if monthly_default_credits is not None:
            settings.monthly_default_credits = monthly_default_credits
        if allow_credit_borrowing is not None:
            settings.allow_credit_borrowing = allow_credit_borrowing
        if allow_emergency_pool is not None:
            settings.allow_emergency_pool = allow_emergency_pool
        if allow_local_models is not None:
            settings.allow_local_models = allow_local_models
        if routing_policy is not None:
            settings.routing_policy = routing_policy

        await self.db.flush()
        return settings

    async def _get_workspace_budget_settings_row(
        self,
        workspace_id: UUID,
    ) -> WorkspaceBudgetSettings | None:
        result = await self.db.execute(
            select(WorkspaceBudgetSettings).where(
                WorkspaceBudgetSettings.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_budget_row(self, workspace_id: UUID, user_id: UUID) -> UserBudget | None:
        result = await self.db.execute(
            select(UserBudget).where(
                UserBudget.workspace_id == workspace_id,
                UserBudget.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
