"""Routing policy unit tests."""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models.ai_account import AIAccount
from app.routing.context import RoutingContext
from app.routing.health import ProviderHealth
from app.routing.policy import (
    BalancedPolicy,
    CheapestPolicy,
    LowestUsagePolicy,
    OwnerFirstPolicy,
    PriorityPolicy,
)


def _account(
    *, provider: str, priority: int = 0, spent: Decimal = Decimal("0"), owner_id=None
) -> AIAccount:
    owner_id = owner_id or uuid4()
    return AIAccount(
        id=uuid4(),
        workspace_id=uuid4(),
        owner_user_id=owner_id,
        provider=provider,
        display_name=provider,
        encrypted_credentials="enc",
        is_active=True,
        monthly_budget=None,
        monthly_spent=spent,
        priority=priority,
        default_model=None,
    )


def _health(account: AIAccount) -> ProviderHealth:
    return ProviderHealth(account=account, is_healthy=True, reason="ok")


def _context(*, owner_id, user_id) -> RoutingContext:
    return RoutingContext(
        workspace=SimpleNamespace(id=uuid4(), owner_id=owner_id, name="WS"),
        requesting_user=SimpleNamespace(id=user_id, name="User"),
        conversation=SimpleNamespace(id=uuid4(), title="Test"),
        provider=None,
        model=None,
        estimated_cost=Decimal("0"),
        participant_user_ids=frozenset({user_id}),
    )


def test_priority_policy_selects_lowest_priority() -> None:
    low = _account(provider="anthropic", priority=0)
    high = _account(provider="anthropic", priority=5)
    result = PriorityPolicy().choose_account(
        _context(owner_id=uuid4(), user_id=uuid4()),
        [_health(high), _health(low)],
        monthly_usage={},
    )
    assert result is not None
    assert result.account.id == low.id


def test_balanced_policy_selects_lowest_spend() -> None:
    cheap = _account(provider="anthropic", priority=0, spent=Decimal("10"))
    costly = _account(provider="anthropic", priority=0, spent=Decimal("100"))
    result = BalancedPolicy().choose_account(
        _context(owner_id=uuid4(), user_id=uuid4()),
        [_health(costly), _health(cheap)],
        monthly_usage={},
    )
    assert result is not None
    assert result.account.id == cheap.id


def test_cheapest_policy_prefers_ollama() -> None:
    ollama = _account(provider="ollama", priority=1)
    anthropic = _account(provider="anthropic", priority=0)
    result = CheapestPolicy().choose_account(
        _context(owner_id=uuid4(), user_id=uuid4()),
        [_health(anthropic), _health(ollama)],
        monthly_usage={},
    )
    assert result is not None
    assert result.account.provider == "ollama"


def test_owner_first_uses_priority_for_owner() -> None:
    owner_id = uuid4()
    primary = _account(provider="anthropic", priority=0)
    secondary = _account(provider="anthropic", priority=1)
    result = OwnerFirstPolicy().choose_account(
        _context(owner_id=owner_id, user_id=owner_id),
        [_health(secondary), _health(primary)],
        monthly_usage={},
    )
    assert result is not None
    assert result.account.id == primary.id


def test_lowest_usage_policy() -> None:
    a = _account(provider="anthropic")
    b = _account(provider="ollama")
    usage = {str(a.id): Decimal("5"), str(b.id): Decimal("1")}
    result = LowestUsagePolicy().choose_account(
        _context(owner_id=uuid4(), user_id=uuid4()),
        [_health(a), _health(b)],
        monthly_usage=usage,
    )
    assert result is not None
    assert result.account.id == b.id
