"""API-level credit and budget verification."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver/api/v1"
        ) as http_client:
            yield http_client


async def _register_and_login(client: AsyncClient) -> str:
    email = f"credits-{uuid4().hex}@example.com"
    password = "password123"
    await client.post(
        "/auth/register",
        json={"name": "Credits User", "email": email, "password": password},
    )
    login = await client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_new_workspace_member_gets_default_budget(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    workspace = await client.post("/workspaces", headers=headers, json={"name": "Credits WS"})
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    budget = await client.get(f"/workspaces/{workspace_id}/budget/me", headers=headers)
    assert budget.status_code == 200
    payload = budget.json()
    assert payload["monthly_credit_limit"] == "5000.00"
    assert payload["remaining_credits"] == "5000.00"
    assert payload["used_credits"] == "0.00"

    history = await client.get(f"/workspaces/{workspace_id}/credits/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] >= 1
    assert history.json()["items"][0]["transaction_type"] == "allocation"
