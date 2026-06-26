from decimal import Decimal

import pytest

from app.resource_management.credit_policy import CreditPolicy


@pytest.fixture
def policy() -> CreditPolicy:
    return CreditPolicy()


def test_ollama_and_mock_are_free(policy: CreditPolicy) -> None:
    assert policy.calculate_cost("ollama", "llama3.2", 5000, 5000) == Decimal("0.00")
    assert policy.calculate_cost("mock", "mock", 10000, 10000) == Decimal("0.00")


def test_anthropic_charges_tokens(policy: CreditPolicy) -> None:
    assert policy.calculate_cost("anthropic", "claude-sonnet-4", 600, 400) == Decimal("1.00")


def test_anthropic_rounds_up(policy: CreditPolicy) -> None:
    assert policy.calculate_cost("anthropic", "claude-sonnet-4", 500, 1) == Decimal("0.51")


def test_unknown_provider_uses_default_multiplier(policy: CreditPolicy) -> None:
    assert policy.calculate_cost("openai", "gpt-5", 1000, 0) == Decimal("1.00")
