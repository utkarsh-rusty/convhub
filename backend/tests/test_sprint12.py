"""Sprint 12 system health and demo login tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import WorkspaceContext


@pytest.fixture
def enable_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_demo_users_hidden_when_disabled(client: AsyncClient) -> None:
    response = await client.get("/demo/users")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_demo_login_hidden_when_disabled(client: AsyncClient) -> None:
    response = await client.post("/demo/login", json={"persona": "alice"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_system_status_requires_admin(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, object],
) -> None:
    _, member = member_workspace
    response = await client.get("/system", headers=member.headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_system_status_for_admin(client: AsyncClient, workspace: WorkspaceContext) -> None:
    response = await client.get("/system", headers=workspace.headers)
    assert response.status_code == 200
    payload = response.json()
    assert "components" in payload
    assert "providers" in payload
    assert any(component["name"] == "Database" for component in payload["components"])


@pytest.mark.asyncio
async def test_demo_users_and_login_when_enabled(
    enable_demo_mode: None,
    client: AsyncClient,
) -> None:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.seed_demo import seed

    await seed()

    users = await client.get("/demo/users")
    assert users.status_code == 200
    personas = {user["persona"] for user in users.json()["users"]}
    assert personas == {"alice", "bob", "charlie"}

    login = await client.post("/demo/login", json={"persona": "alice"})
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert login.json()["workspace_slug"] == "demo"
