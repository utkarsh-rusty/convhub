from __future__ import annotations

from uuid import UUID

from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType
from app.models.user import User


def _user_name(user: User | None, user_id: UUID | None) -> str:
    if user is not None and user.name.strip():
        return user.name.strip()
    return "Unknown user"


def format_credit_transaction_display(
    transaction: CreditTransaction,
    viewer_user_id: UUID,
) -> str:
    """Viewer-aware label for credit history (uses names, not raw UUIDs)."""
    lender_id = transaction.from_user_id
    borrower_id = transaction.to_user_id
    lender_name = _user_name(transaction.from_user, lender_id)
    borrower_name = _user_name(transaction.to_user, borrower_id)

    match transaction.transaction_type:
        case CreditTransactionType.BORROW:
            if viewer_user_id == borrower_id:
                return f"You borrowed credits from {lender_name}"
            if viewer_user_id == lender_id:
                return f"{borrower_name} borrowed credits from you"
            return f"{borrower_name} borrowed credits from {lender_name}"
        case CreditTransactionType.LEND:
            if viewer_user_id == lender_id:
                return f"You lent credits to {borrower_name}"
            if viewer_user_id == borrower_id:
                return f"{lender_name} lent credits to you"
            return f"{lender_name} lent credits to {borrower_name}"
        case CreditTransactionType.ADJUSTMENT:
            if lender_id and borrower_id:
                if viewer_user_id == borrower_id:
                    return f"You returned borrowed credits to {lender_name}"
                if viewer_user_id == lender_id:
                    return f"{borrower_name} returned borrowed credits to you"
                return f"{borrower_name} returned borrowed credits to {lender_name}"
            return transaction.description
        case _:
            return transaction.description
