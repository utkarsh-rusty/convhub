from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.models.enums import BorrowStrategyType
from app.models.lending_preference import LendingPreference
from app.models.user_budget import UserBudget


@dataclass(frozen=True)
class LenderCandidate:
    user_id: UUID
    preference: LendingPreference
    budget: UserBudget

    @property
    def shareable_credits(self) -> Decimal:
        return self.budget.remaining_credits - self.preference.minimum_reserved_credits

    @property
    def remaining_share_capacity(self) -> Decimal:
        if self.preference.monthly_share_limit <= Decimal("0"):
            return Decimal("0")
        return self.preference.monthly_share_limit - self.budget.lent_credits


class BorrowStrategy(ABC):
    strategy_type: BorrowStrategyType

    @abstractmethod
    def select_lender(
        self,
        candidates: list[LenderCandidate],
        amount: Decimal,
    ) -> LenderCandidate | None:
        """Pick the best lender that can cover the full amount."""

    def order_lenders(self, candidates: list[LenderCandidate]) -> list[LenderCandidate]:
        """Return lenders sorted by preference for routing attempts."""
        return sorted(
            candidates,
            key=lambda candidate: (
                candidate.remaining_share_capacity,
                -candidate.preference.priority,
            ),
            reverse=True,
        )


class HighestRemainingStrategy(BorrowStrategy):
    strategy_type = BorrowStrategyType.HIGHEST_REMAINING

    def select_lender(
        self,
        candidates: list[LenderCandidate],
        amount: Decimal,
    ) -> LenderCandidate | None:
        eligible = [
            candidate for candidate in candidates if candidate.remaining_share_capacity >= amount
        ]
        if not eligible:
            return None

        return max(
            eligible,
            key=lambda candidate: (
                candidate.remaining_share_capacity,
                -candidate.preference.priority,
            ),
        )


STRATEGY_REGISTRY: dict[BorrowStrategyType, BorrowStrategy] = {
    BorrowStrategyType.HIGHEST_REMAINING: HighestRemainingStrategy(),
}


def get_borrow_strategy(strategy_type: BorrowStrategyType) -> BorrowStrategy:
    return STRATEGY_REGISTRY[strategy_type]
