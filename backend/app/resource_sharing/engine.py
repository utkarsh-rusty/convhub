from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrow_record import BorrowRecord
from app.models.credit_transaction import CreditTransaction
from app.models.enums import BorrowStrategyType, CreditTransactionType
from app.models.lending_preference import LendingPreference
from app.models.user import User
from app.models.user_budget import UserBudget
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_sharing.strategy import (
    BorrowStrategy,
    LenderCandidate,
    get_borrow_strategy,
)


@dataclass(frozen=True)
class BorrowReservation:
    workspace_id: UUID
    borrower_user_id: UUID
    lender_user_id: UUID
    amount: Decimal
    strategy: BorrowStrategyType


class BorrowEngine:
    def __init__(
        self,
        db: AsyncSession,
        budget_service: BudgetService,
        strategy: BorrowStrategy | None = None,
    ) -> None:
        self.db = db
        self.budget_service = budget_service
        self.strategy = strategy or get_borrow_strategy(BorrowStrategyType.HIGHEST_REMAINING)

    async def find_lenders(
        self,
        workspace_id: UUID,
        borrower_user_id: UUID,
        amount: Decimal,
        *,
        eligible_user_ids: frozenset[UUID] | None = None,
    ) -> list[LenderCandidate]:
        result = await self.db.execute(
            select(LendingPreference, UserBudget)
            .join(
                UserBudget,
                (UserBudget.workspace_id == LendingPreference.workspace_id)
                & (UserBudget.user_id == LendingPreference.user_id),
            )
            .join(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == LendingPreference.workspace_id)
                & (WorkspaceMember.user_id == LendingPreference.user_id),
            )
            .where(
                LendingPreference.workspace_id == workspace_id,
                LendingPreference.user_id != borrower_user_id,
                LendingPreference.auto_share_enabled.is_(True),
                LendingPreference.monthly_share_limit > Decimal("0"),
            )
        )

        candidates: list[LenderCandidate] = []
        for preference, budget in result.all():
            if eligible_user_ids is not None and preference.user_id not in eligible_user_ids:
                continue
            await self.budget_service.reset_if_needed(workspace_id, preference.user_id)
            candidate = LenderCandidate(
                user_id=preference.user_id,
                preference=preference,
                budget=budget,
            )
            if self.validate_lender(preference, budget, amount):
                candidates.append(candidate)

        return candidates

    def validate_lender(
        self,
        preference: LendingPreference,
        budget: UserBudget,
        amount: Decimal,
    ) -> bool:
        if amount <= Decimal("0"):
            return False
        if not preference.auto_share_enabled:
            return False
        if preference.monthly_share_limit <= Decimal("0"):
            return False

        remaining_share = preference.monthly_share_limit - budget.lent_credits
        if remaining_share < amount:
            return False

        if budget.remaining_credits - amount < preference.minimum_reserved_credits:
            return False

        return True

    async def find_eligible_lenders(
        self,
        workspace_id: UUID,
        borrower_user_id: UUID,
        *,
        eligible_user_ids: frozenset[UUID] | None = None,
    ) -> list[LenderCandidate]:
        """Lenders with auto-share enabled and remaining share capacity."""
        result = await self.db.execute(
            select(LendingPreference, UserBudget)
            .join(
                UserBudget,
                (UserBudget.workspace_id == LendingPreference.workspace_id)
                & (UserBudget.user_id == LendingPreference.user_id),
            )
            .join(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == LendingPreference.workspace_id)
                & (WorkspaceMember.user_id == LendingPreference.user_id),
            )
            .where(
                LendingPreference.workspace_id == workspace_id,
                LendingPreference.user_id != borrower_user_id,
                LendingPreference.auto_share_enabled.is_(True),
                LendingPreference.monthly_share_limit > Decimal("0"),
            )
        )

        candidates: list[LenderCandidate] = []
        for preference, budget in result.all():
            if eligible_user_ids is not None and preference.user_id not in eligible_user_ids:
                continue
            await self.budget_service.reset_if_needed(workspace_id, preference.user_id)
            candidate = LenderCandidate(
                user_id=preference.user_id,
                preference=preference,
                budget=budget,
            )
            if candidate.remaining_share_capacity > Decimal("0"):
                candidates.append(candidate)

        return candidates

    async def reserve_shared_credits(
        self,
        workspace_id: UUID,
        borrower_user_id: UUID,
        amount: Decimal,
        *,
        eligible_user_ids: frozenset[UUID] | None = None,
    ) -> BorrowReservation | None:
        if amount <= Decimal("0"):
            return None

        candidates = await self.find_lenders(
            workspace_id,
            borrower_user_id,
            amount,
            eligible_user_ids=eligible_user_ids,
        )
        lender = self.strategy.select_lender(candidates, amount)
        if lender is None:
            return None

        await self.budget_service.reset_if_needed(workspace_id, lender.user_id)
        await self.budget_service.reset_if_needed(workspace_id, borrower_user_id)

        lender_budget = await self.budget_service.get_budget(workspace_id, lender.user_id)
        borrower_budget = await self.budget_service.get_budget(workspace_id, borrower_user_id)

        if not self.validate_lender(lender.preference, lender_budget, amount):
            return None

        user_names = await self._load_user_names(lender.user_id, borrower_user_id)
        lender_name = user_names[lender.user_id]
        borrower_name = user_names[borrower_user_id]

        lend_transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=None,
            from_user_id=lender.user_id,
            to_user_id=borrower_user_id,
            transaction_type=CreditTransactionType.LEND,
            amount=amount,
            description=f"{lender_name} lent credits to {borrower_name}",
        )
        self.db.add(lend_transaction)

        lender_budget.remaining_credits -= amount
        lender_budget.lent_credits += amount

        borrow_transaction = CreditTransaction(
            workspace_id=workspace_id,
            request_id=None,
            from_user_id=lender.user_id,
            to_user_id=borrower_user_id,
            transaction_type=CreditTransactionType.BORROW,
            amount=amount,
            description=f"{borrower_name} borrowed credits from {lender_name}",
        )
        self.db.add(borrow_transaction)

        borrower_budget.remaining_credits += amount
        borrower_budget.borrowed_credits += amount

        await self.db.flush()

        return BorrowReservation(
            workspace_id=workspace_id,
            borrower_user_id=borrower_user_id,
            lender_user_id=lender.user_id,
            amount=amount,
            strategy=self.strategy.strategy_type,
        )

    async def record_borrow(
        self,
        request_id: UUID,
        reservation: BorrowReservation,
    ) -> BorrowRecord:
        record = BorrowRecord(
            request_id=request_id,
            workspace_id=reservation.workspace_id,
            borrower_user_id=reservation.borrower_user_id,
            lender_user_id=reservation.lender_user_id,
            credits=reservation.amount,
            strategy=reservation.strategy.value,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def release_borrow(self, reservation: BorrowReservation) -> None:
        if reservation.amount <= Decimal("0"):
            return

        lender_budget = await self.budget_service.get_budget(
            reservation.workspace_id,
            reservation.lender_user_id,
        )
        borrower_budget = await self.budget_service.get_budget(
            reservation.workspace_id,
            reservation.borrower_user_id,
        )

        user_names = await self._load_user_names(
            reservation.lender_user_id,
            reservation.borrower_user_id,
        )
        lender_name = user_names[reservation.lender_user_id]
        borrower_name = user_names[reservation.borrower_user_id]

        self.db.add(
            CreditTransaction(
                workspace_id=reservation.workspace_id,
                request_id=None,
                from_user_id=reservation.borrower_user_id,
                to_user_id=reservation.lender_user_id,
                transaction_type=CreditTransactionType.ADJUSTMENT,
                amount=reservation.amount,
                description=f"{borrower_name} returned borrowed credits to {lender_name}",
            )
        )
        lender_budget.remaining_credits += reservation.amount
        lender_budget.lent_credits = max(
            Decimal("0"), lender_budget.lent_credits - reservation.amount
        )

        borrower_budget.remaining_credits = max(
            Decimal("0"),
            borrower_budget.remaining_credits - reservation.amount,
        )
        borrower_budget.borrowed_credits = max(
            Decimal("0"),
            borrower_budget.borrowed_credits - reservation.amount,
        )

        await self.db.flush()

    async def _load_user_names(self, *user_ids: UUID) -> dict[UUID, str]:
        unique_ids = list(dict.fromkeys(user_ids))
        if not unique_ids:
            return {}

        result = await self.db.execute(select(User).where(User.id.in_(unique_ids)))
        users = result.scalars().all()
        names = {user.id: user.name.strip() for user in users if user.name.strip()}
        return {user_id: names.get(user_id, "Unknown user") for user_id in unique_ids}
