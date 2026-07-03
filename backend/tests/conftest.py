"""Shared pytest fixtures and helpers for API integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def disable_demo_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEMO_MODE", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()


@dataclass
class AuthContext:
    token: str
    user_id: str
    email: str
    name: str
    headers: dict[str, str]


@dataclass
class WorkspaceContext:
    workspace_id: str
    headers: dict[str, str]
    auth: AuthContext


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver/api/v1"
        ) as http_client:
            yield http_client


async def register_user(
    client: AsyncClient,
    *,
    name: str | None = None,
    email: str | None = None,
    password: str = "password123",
) -> AuthContext:
    email = email or f"user-{uuid4().hex}@example.com"
    name = name or "Test User"
    response = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    login = await client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return AuthContext(
        token=token,
        user_id=user_id,
        email=email,
        name=name,
        headers={"Authorization": f"Bearer {token}"},
    )


async def create_workspace(
    client: AsyncClient,
    auth: AuthContext,
    *,
    name: str | None = None,
) -> WorkspaceContext:
    response = await client.post(
        "/workspaces",
        headers=auth.headers,
        json={"name": name or f"Workspace {uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    workspace_id = response.json()["id"]
    headers = {
        **auth.headers,
        "X-Workspace-ID": workspace_id,
    }
    return WorkspaceContext(workspace_id=workspace_id, headers=headers, auth=auth)


async def invite_and_accept(
    client: AsyncClient,
    workspace: WorkspaceContext,
    invitee: AuthContext,
    *,
    role: str = "member",
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": invitee.email, "role": role},
    )
    assert invite.status_code == 201, invite.text
    accept = await client.post(
        f"/invitations/{invite.json()['token']}/accept",
        headers=invitee.headers,
    )
    assert accept.status_code == 200, accept.text


@pytest.fixture
async def auth_user(client: AsyncClient) -> AuthContext:
    return await register_user(client)


@pytest.fixture
async def workspace(client: AsyncClient, auth_user: AuthContext) -> WorkspaceContext:
    return await create_workspace(client, auth_user)


@pytest.fixture
async def second_user(client: AsyncClient) -> AuthContext:
    return await register_user(client, name="Second User")


@pytest.fixture
async def member_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> tuple[WorkspaceContext, AuthContext]:
    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    return workspace, AuthContext(
        token=second_user.token,
        user_id=second_user.user_id,
        email=second_user.email,
        name=second_user.name,
        headers=member_headers,
    )
