from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lending_preference import (
    DEFAULT_MINIMUM_RESERVED_CREDITS,
    LendingPreference,
)
from app.models.user import User
from app.models.user_budget import UserBudget
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService


class LendingPreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_preference(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> LendingPreference:
        existing = await self._get_preference_row(workspace_id, user_id)
        if existing is not None:
            return existing

        preference = LendingPreference(
            workspace_id=workspace_id,
            user_id=user_id,
            auto_share_enabled=False,
            monthly_share_limit=Decimal("0"),
            minimum_reserved_credits=DEFAULT_MINIMUM_RESERVED_CREDITS,
            priority=0,
        )
        self.db.add(preference)
        await self.db.flush()
        return preference

    async def get_my_preference(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> LendingPreference:
        preference = await self._get_preference_row(workspace_id, user_id)
        if preference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lending preference not found",
            )
        return preference

    async def update_my_preference(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        auto_share_enabled: bool | None = None,
        monthly_share_limit: Decimal | None = None,
        minimum_reserved_credits: Decimal | None = None,
        priority: int | None = None,
    ) -> LendingPreference:
        preference = await self.get_my_preference(workspace_id, user_id)

        if auto_share_enabled is not None:
            preference.auto_share_enabled = auto_share_enabled
        if monthly_share_limit is not None:
            if monthly_share_limit < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Monthly share limit cannot be negative",
                )
            preference.monthly_share_limit = monthly_share_limit
        if minimum_reserved_credits is not None:
            if minimum_reserved_credits < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Minimum reserved credits cannot be negative",
                )
            preference.minimum_reserved_credits = minimum_reserved_credits
        if priority is not None:
            preference.priority = priority

        await self.db.flush()
        return preference

    async def list_workspace_sharing(
        self,
        workspace_id: UUID,
        budget_service: BudgetService,
    ) -> list[dict]:
        result = await self.db.execute(
            select(LendingPreference, UserBudget, User)
            .join(
                UserBudget,
                (UserBudget.workspace_id == LendingPreference.workspace_id)
                & (UserBudget.user_id == LendingPreference.user_id),
            )
            .join(User, User.id == LendingPreference.user_id)
            .join(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == LendingPreference.workspace_id)
                & (WorkspaceMember.user_id == LendingPreference.user_id),
            )
            .where(LendingPreference.workspace_id == workspace_id)
            .order_by(User.name.asc())
        )

        rows: list[dict] = []
        for preference, budget, user in result.all():
            await budget_service.reset_if_needed(workspace_id, preference.user_id)
            rows.append(
                {
                    "user_id": preference.user_id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "auto_share_enabled": preference.auto_share_enabled,
                    "monthly_share_limit": preference.monthly_share_limit,
                    "minimum_reserved_credits": preference.minimum_reserved_credits,
                    "priority": preference.priority,
                    "remaining_credits": budget.remaining_credits,
                    "borrowed_credits": budget.borrowed_credits,
                    "lent_credits": budget.lent_credits,
                }
            )
        return rows

    async def _get_preference_row(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> LendingPreference | None:
        result = await self.db.execute(
            select(LendingPreference).where(
                LendingPreference.workspace_id == workspace_id,
                LendingPreference.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
