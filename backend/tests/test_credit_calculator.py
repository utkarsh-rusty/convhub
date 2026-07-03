from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.ai_request import AIRequest
from app.models.enums import AIRequestStatus
from app.resource_management.credit_calculator import calculate_credits


def _make_ai_request(
    *,
    input_tokens: int,
    output_tokens: int,
    provider: str = "anthropic",
) -> AIRequest:
    return AIRequest(
        id=uuid4(),
        conversation_id=uuid4(),
        user_message_id=uuid4(),
        provider=provider,
        model="claude-sonnet-4",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def test_calculate_credits_exact_thousand_tokens() -> None:
    request = _make_ai_request(input_tokens=600, output_tokens=400)
    assert calculate_credits(request) == Decimal("1.00")


def test_calculate_credits_rounds_up() -> None:
    request = _make_ai_request(input_tokens=500, output_tokens=1)
    assert calculate_credits(request) == Decimal("0.51")


def test_calculate_credits_zero_tokens() -> None:
    request = _make_ai_request(input_tokens=0, output_tokens=0)
    assert calculate_credits(request) == Decimal("0.00")


def test_calculate_credits_mock_provider_is_free() -> None:
    request = _make_ai_request(input_tokens=5000, output_tokens=5000, provider="mock")
    assert calculate_credits(request) == Decimal("0.00")


def test_calculate_credits_handles_null_tokens() -> None:
    request = _make_ai_request(input_tokens=0, output_tokens=0)
    request.input_tokens = None
    request.output_tokens = None
    assert calculate_credits(request) == Decimal("0.00")
