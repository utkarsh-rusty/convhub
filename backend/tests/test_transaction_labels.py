from decimal import Decimal
from uuid import uuid4

from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType
from app.models.user import User
from app.resource_management.transaction_labels import format_credit_transaction_display


def _tx(
    *,
    transaction_type: CreditTransactionType,
    from_user: User | None = None,
    to_user: User | None = None,
    description: str = "ledger entry",
) -> CreditTransaction:
    return CreditTransaction(
        workspace_id=uuid4(),
        request_id=None,
        from_user_id=from_user.id if from_user else None,
        to_user_id=to_user.id if to_user else None,
        transaction_type=transaction_type,
        amount=Decimal("10.00"),
        description=description,
        from_user=from_user,
        to_user=to_user,
    )


def test_borrow_transaction_uses_names_for_borrower_view() -> None:
    lender = User(id=uuid4(), email="a@example.com", name="Alice", password_hash="x")
    borrower = User(id=uuid4(), email="b@example.com", name="Bob", password_hash="x")
    tx = _tx(
        transaction_type=CreditTransactionType.BORROW,
        from_user=lender,
        to_user=borrower,
        description="Borrow credits from user old-id",
    )

    assert format_credit_transaction_display(tx, borrower.id) == (
        "You borrowed credits from Alice"
    )


def test_lend_transaction_uses_names_for_lender_view() -> None:
    lender = User(id=uuid4(), email="a@example.com", name="Alice", password_hash="x")
    borrower = User(id=uuid4(), email="b@example.com", name="Bob", password_hash="x")
    tx = _tx(
        transaction_type=CreditTransactionType.LEND,
        from_user=lender,
        to_user=borrower,
        description="Lend credits to user old-id",
    )

    assert format_credit_transaction_display(tx, lender.id) == "You lent credits to Bob"
    assert format_credit_transaction_display(tx, borrower.id) == "Alice lent credits to you"


def test_borrow_transaction_shows_both_parties_for_lender_view() -> None:
    lender = User(id=uuid4(), email="a@example.com", name="Alice", password_hash="x")
    borrower = User(id=uuid4(), email="b@example.com", name="Bob", password_hash="x")
    tx = _tx(
        transaction_type=CreditTransactionType.BORROW,
        from_user=lender,
        to_user=borrower,
    )

    assert format_credit_transaction_display(tx, lender.id) == (
        "Bob borrowed credits from you"
    )
