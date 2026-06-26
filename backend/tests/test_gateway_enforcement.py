"""Gateway budget enforcement tests."""

from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.ai_request import AIRequest
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as http_client:
            yield http_client


async def _register(client: AsyncClient) -> str:
    email = f"gateway-{uuid4().hex}@example.com"
    password = "password123"
    await client.post(
        "/auth/register",
        json={"name": "Gateway User", "email": email, "password": password},
    )
    login = await client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_gateway_blocks_paid_provider_with_zero_credits(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    get_settings.cache_clear()

    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    workspace = await client.post("/workspaces", headers=headers, json={"name": "Zero Credits WS"})
    workspace_id = workspace.json()["id"]
    headers["X-Workspace-ID"] = workspace_id

    session_factory = app.state.session_factory
    async with session_factory() as db:
        member_result = await db.execute(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
        user_id = member_result.scalar_one()
        service = BudgetService(db)
        budget = await service.get_budget(workspace_id, user_id)
        budget.remaining_credits = Decimal("0")
        budget.used_credits = budget.monthly_credit_limit
        await db.commit()

    conv = await client.post("/conversations", headers=headers, json={"title": "Blocked"})
    conv_id = conv.json()["id"]

    response = await client.post(
        "/chat/send",
        headers=headers,
        json={"conversation_id": conv_id, "content": "Hello"},
    )
    assert response.status_code == 402

    async with session_factory() as db:
        result = await db.execute(select(AIRequest).where(AIRequest.conversation_id == conv_id))
        assert result.scalar_one_or_none() is None

    get_settings.cache_clear()
