"""Tests for Sprint 10.5 Demo & Testing Toolkit."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import ChatMessage
from app.demo.context import DemoRuntimeContext, reset_demo_runtime, set_demo_runtime
from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)
from app.resource_management.credit_policy import CreditPolicy
from app.resource_management.pricing_engine import PricingEngine
from tests.conftest import AuthContext, WorkspaceContext, create_workspace, register_user


@pytest.fixture
def enable_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEMO_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def demo_runtime() -> DemoRuntimeContext:
    return DemoRuntimeContext(
        workspace_id=uuid4(),
        pricing_profile=PricingProfileType.DEMO,
        provider_simulation=ProviderSimulationMode.NORMAL,
        routing_override_mode=RoutingOverrideMode.NORMAL,
        routing_override_account_id=None,
    )


def test_pricing_engine_production_profile() -> None:
    engine = PricingEngine()
    assert engine.multiplier_for(PricingProfileType.PRODUCTION, "ollama") == Decimal("0.00")
    assert engine.multiplier_for(PricingProfileType.PRODUCTION, "anthropic") == Decimal("1.0")


def test_pricing_engine_demo_profile() -> None:
    engine = PricingEngine()
    assert engine.multiplier_for(PricingProfileType.DEMO, "ollama") == Decimal("1.0")
    assert engine.multiplier_for(PricingProfileType.DEMO, "mock") == Decimal("1.0")


def test_pricing_engine_free_profile() -> None:
    engine = PricingEngine()
    assert engine.multiplier_for(PricingProfileType.FREE, "anthropic") == Decimal("0.00")


def test_credit_policy_uses_demo_profile_from_context(demo_runtime: DemoRuntimeContext) -> None:
    policy = CreditPolicy()
    token = set_demo_runtime(demo_runtime)
    try:
        cost = policy.calculate_cost("ollama", "llama3.2", 1000, 1000)
        assert cost == Decimal("2.00")
    finally:
        reset_demo_runtime(token)


def test_credit_policy_production_without_context() -> None:
    policy = CreditPolicy()
    cost = policy.calculate_cost("ollama", "llama3.2", 1000, 1000)
    assert cost == Decimal("0.00")


@pytest.mark.asyncio
async def test_demo_config_disabled_by_default(client: AsyncClient) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    response = await client.get("/demo/config")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_demo_endpoints_hidden_when_disabled(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    response = await client.get(
        f"/workspaces/{workspace.workspace_id}/demo",
        headers=workspace.headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_demo_endpoints_require_admin(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
    enable_demo_mode: None,
) -> None:
    workspace, member = member_workspace
    member_headers = {**member.headers, "X-Workspace-ID": workspace.workspace_id}
    response = await client.get(
        f"/workspaces/{workspace.workspace_id}/demo",
        headers=member_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pricing_profile_update(
    client: AsyncClient,
    workspace: WorkspaceContext,
    enable_demo_mode: None,
) -> None:
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}/demo/pricing-profile",
        headers=workspace.headers,
        json={"pricing_profile": "demo"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["pricing_profile"] == "demo"


@pytest.mark.asyncio
async def test_set_user_credits_creates_adjustment(
    client: AsyncClient,
    workspace: WorkspaceContext,
    enable_demo_mode: None,
) -> None:
    set_response = await client.post(
        f"/workspaces/{workspace.workspace_id}/demo/credits/set",
        headers=workspace.headers,
        json={"user_id": workspace.auth.user_id, "remaining_credits": "2.00"},
    )
    assert set_response.status_code == 200, set_response.text
    assert set_response.json()["budget"]["remaining_credits"] == "2.00"

    history = await client.get(
        f"/workspaces/{workspace.workspace_id}/credits/history",
        headers=workspace.headers,
    )
    assert history.status_code == 200
    types = {item["transaction_type"] for item in history.json()["items"]}
    assert "adjustment" in types


@pytest.mark.asyncio
async def test_reset_user_credits(
    client: AsyncClient,
    workspace: WorkspaceContext,
    enable_demo_mode: None,
) -> None:
    await client.post(
        f"/workspaces/{workspace.workspace_id}/demo/credits/set",
        headers=workspace.headers,
        json={"user_id": workspace.auth.user_id, "remaining_credits": "1.00"},
    )
    reset = await client.post(
        f"/workspaces/{workspace.workspace_id}/demo/credits/reset-user",
        headers=workspace.headers,
        params={"user_id": workspace.auth.user_id},
    )
    assert reset.status_code == 200, reset.text
    remaining = Decimal(reset.json()["budget"]["remaining_credits"])
    limit = Decimal(reset.json()["budget"]["monthly_credit_limit"])
    assert remaining == limit


@pytest.mark.asyncio
async def test_provider_simulation_timeout_refunds(
    client: AsyncClient,
    workspace: WorkspaceContext,
    enable_demo_mode: None,
) -> None:
    await client.patch(
        f"/workspaces/{workspace.workspace_id}/settings/budget",
        headers=workspace.headers,
        json={"allow_credit_borrowing": True},
    )
    await client.patch(
        f"/workspaces/{workspace.workspace_id}/demo/pricing-profile",
        headers=workspace.headers,
        json={"pricing_profile": "demo"},
    )
    await client.patch(
        f"/workspaces/{workspace.workspace_id}/demo/provider-simulation",
        headers=workspace.headers,
        json={"provider_simulation": "timeout"},
    )
    await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Mock Demo",
            "api_key": "test-key",
            "is_active": True,
            "priority": 1,
        },
    )

    conv = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Demo timeout"},
    )
    assert conv.status_code == 201, conv.text
    conversation_id = conv.json()["id"]

    before = await client.get(
        f"/workspaces/{workspace.workspace_id}/budget/me",
        headers=workspace.headers,
    )
    before_remaining = Decimal(before.json()["remaining_credits"])

    send = await client.post(
        "/chat/send",
        headers=workspace.headers,
        json={"conversation_id": conversation_id, "content": "trigger timeout"},
    )
    assert send.status_code == 502, send.text

    after = await client.get(
        f"/workspaces/{workspace.workspace_id}/budget/me",
        headers=workspace.headers,
    )
    after_remaining = Decimal(after.json()["remaining_credits"])
    assert after_remaining == before_remaining


@pytest.mark.asyncio
async def test_routing_override_first_account(
    client: AsyncClient,
    workspace: WorkspaceContext,
    enable_demo_mode: None,
) -> None:
    first = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "First",
            "api_key": "test-key",
            "is_active": True,
            "priority": 1,
        },
    )
    second = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Second",
            "api_key": "test-key-2",
            "is_active": True,
            "priority": 2,
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    await client.patch(
        f"/workspaces/{workspace.workspace_id}/demo/routing-override",
        headers=workspace.headers,
        json={"routing_override_mode": "first_account"},
    )

    routing = await client.get(
        f"/workspaces/{workspace.workspace_id}/routing",
        headers=workspace.headers,
    )
    assert routing.status_code == 200, routing.text
    assert routing.json()["preview"]["selected_account_id"] == first.json()["id"]
    assert "Demo routing override" in routing.json()["preview"]["decision_reason"]


@pytest.mark.asyncio
async def test_simulated_failure_provider_raises_before_inner() -> None:
    from app.demo.runtime import SimulatedFailureProvider

    inner = AsyncMock()
    provider = SimulatedFailureProvider(inner, ProviderSimulationMode.TIMEOUT)
    prompt = PromptContext(system_prompt="hi", chat_messages=[ChatMessage("user", "hello")])

    with pytest.raises(TimeoutError):
        await provider.generate(prompt, "mock")

    inner.generate.assert_not_called()
