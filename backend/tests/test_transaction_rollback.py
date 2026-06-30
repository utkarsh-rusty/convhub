"""Transaction rollback and data integrity regression tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_failed_duplicate_registration_leaves_single_user(client: AsyncClient) -> None:
    email = f"rollback-{uuid4().hex}@example.com"
    first = await client.post(
        "/auth/register",
        json={"name": "Rollback User", "email": email, "password": "password123"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/register",
        json={"name": "Rollback Duplicate", "email": email, "password": "password123"},
    )
    assert second.status_code == 409

    session_factory = app.state.session_factory
    async with session_factory() as db:
        count = await db.execute(select(func.count()).select_from(User).where(User.email == email))
        assert int(count.scalar_one()) == 1


@pytest.mark.asyncio
async def test_failed_chat_request_does_not_persist_ai_request_on_provider_error(
    client: AsyncClient,
    workspace,
    monkeypatch,
) -> None:
    def failing_provider(**_kwargs):
        raise ValueError("Provider unavailable")

    monkeypatch.setattr("app.ai.gateway.create_provider", failing_provider)

    conv = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Rollback Chat"},
    )
    conv_id = conv.json()["id"]

    response = await client.post(
        "/chat/send",
        headers=workspace.headers,
        json={"conversation_id": conv_id, "content": "This should fail"},
    )
    assert response.status_code == 503

    from app.models.ai_request import AIRequest

    session_factory = app.state.session_factory
    async with session_factory() as db:
        result = await db.execute(select(AIRequest).where(AIRequest.conversation_id == conv_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_invalid_sharing_update_does_not_persist_negative_limit(
    client: AsyncClient,
    workspace,
) -> None:
    before = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing/me",
        headers=workspace.headers,
    )
    assert before.status_code == 200
    original_limit = before.json()["monthly_share_limit"]

    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}/sharing/me",
        headers=workspace.headers,
        json={"monthly_share_limit": "-10"},
    )
    assert response.status_code == 422

    after = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing/me",
        headers=workspace.headers,
    )
    assert after.json()["monthly_share_limit"] == original_limit
