"""AI account API QA tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import AuthContext, WorkspaceContext


@pytest.mark.asyncio
async def test_ai_account_crud_happy_path(client: AsyncClient, workspace: WorkspaceContext) -> None:
    created = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "QA Mock Account",
            "api_key": "test-key",
            "is_active": True,
            "priority": 1,
            "default_model": "mock",
        },
    )
    assert created.status_code == 201
    account_id = created.json()["id"]

    listed = await client.get("/ai-accounts", headers=workspace.headers)
    assert listed.status_code == 200
    assert any(account["id"] == account_id for account in listed.json())

    updated = await client.patch(
        f"/ai-accounts/{account_id}",
        headers=workspace.headers,
        json={"display_name": "Renamed Mock", "priority": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Renamed Mock"
    assert updated.json()["priority"] == 2

    deleted = await client.delete(f"/ai-accounts/{account_id}", headers=workspace.headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_ollama_account_does_not_require_api_key(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    response = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "ollama",
            "display_name": "Local Ollama",
            "is_active": True,
            "priority": 0,
            "default_model": "llama3.2",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_anthropic_account_requires_api_key(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    response = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "anthropic",
            "display_name": "Missing Key",
            "is_active": True,
            "priority": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_member_cannot_manage_ai_accounts(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    _, member = member_workspace
    response = await client.get("/ai-accounts", headers=member.headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ai_accounts_require_workspace_header(
    client: AsyncClient,
    auth_user: AuthContext,
) -> None:
    response = await client.get("/ai-accounts", headers=auth_user.headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_test_ai_account_endpoint(client: AsyncClient, workspace: WorkspaceContext) -> None:
    created = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Testable Mock",
            "api_key": "test-key",
            "is_active": True,
            "priority": 0,
        },
    )
    account_id = created.json()["id"]
    response = await client.post(f"/ai-accounts/{account_id}/test", headers=workspace.headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
