"""Tests for Sprint 29 — Workspace Client API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import AuthContext, WorkspaceContext, create_workspace, invite_and_accept


async def _create_project(client: AsyncClient, workspace: WorkspaceContext) -> str:
    response = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Client Lab"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    project_id: str,
    name: str = "plugin-repo",
) -> dict:
    response = await client.post(
        "/repositories",
        headers=workspace.headers,
        json={
            "project_id": project_id,
            "name": name,
            "provider": "github",
            "owner": "convhub",
            "repository_name": name,
            "remote_url": f"https://github.com/convhub/{name}",
            "default_branch": "main",
            "visibility": "private",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    name: str = "main",
    is_default: bool = True,
) -> dict:
    response = await client.post(
        f"/repositories/{repository_id}/branches",
        headers=workspace.headers,
        json={"name": name, "is_default": is_default},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    project_id: str,
    title: str = "Plugin session",
) -> dict:
    response = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": title, "project_id": project_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _enable_and_attach(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
    repository_id: str,
) -> None:
    enable = await client.post(
        f"/conversations/{conversation_id}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert enable.status_code == 200, enable.text
    attach = await client.post(
        f"/conversations/{conversation_id}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository_id},
    )
    assert attach.status_code == 200, attach.text


async def _setup(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> tuple[dict, dict, dict]:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    return repository, branch, conversation


async def _connect(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    repository_branch_id: str,
    conversation_id: str,
    client_name: str = "vscode",
) -> dict:
    response = await client.post(
        "/workspace-client/connect",
        headers=workspace.headers,
        json={
            "repository_id": repository_id,
            "repository_branch_id": repository_branch_id,
            "conversation_id": conversation_id,
            "client_name": client_name,
            "client_version": "1.0.0",
            "platform": "darwin",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_workspace_client_connect(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    body = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    assert body["workspace_session_id"]
    assert body["resumed"] is False
    assert body["session_status"] == "active"
    assert body["current_branch_version"] >= 1
    assert body["current_memory_version"] >= 1
    assert body["sync_state"] in {"synced", "ahead", "behind", "conflict", "detached"}


@pytest.mark.asyncio
async def test_workspace_client_reconnect(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    first = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        client_name="cursor",
    )
    second = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        client_name="cursor",
    )
    assert second["resumed"] is True
    assert second["workspace_session_id"] == first["workspace_session_id"]


@pytest.mark.asyncio
async def test_workspace_client_heartbeat(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    connected = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    response = await client.post(
        "/workspace-client/heartbeat",
        headers=workspace.headers,
        json={"workspace_session_id": connected["workspace_session_id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workspace_session_id"] == connected["workspace_session_id"]
    assert body["status"] == "active"
    assert body["last_heartbeat_at"] is not None


@pytest.mark.asyncio
async def test_workspace_client_push_and_pull(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    connected = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    session_id = connected["workspace_session_id"]

    push = await client.post(
        "/workspace-client/push",
        headers=workspace.headers,
        json={"workspace_session_id": session_id, "notes": "plugin push"},
    )
    assert push.status_code == 200, push.text
    push_body = push.json()
    assert push_body["sync_version"] >= connected["current_branch_version"]
    assert push_body["sync_state"] in {"synced", "ahead", "behind", "conflict", "detached"}

    pull = await client.get(
        "/workspace-client/pull",
        headers=workspace.headers,
        params={"workspace_session_id": session_id},
    )
    assert pull.status_code == 200, pull.text
    pull_body = pull.json()
    assert pull_body["workspace_session_id"] == session_id
    assert pull_body["branch_memory"]["repository_branch_id"] == branch["id"]
    assert pull_body["sync_version"] == push_body["sync_version"]
    assert pull_body["branch_version"] == push_body["sync_version"]
    assert pull_body["active_developer"] is not None


@pytest.mark.asyncio
async def test_workspace_client_disconnect(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    connected = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    response = await client.post(
        "/workspace-client/disconnect",
        headers=workspace.headers,
        json={"workspace_session_id": connected["workspace_session_id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    assert response.json()["closed_at"] is not None

    heartbeat = await client.post(
        "/workspace-client/heartbeat",
        headers=workspace.headers,
        json={"workspace_session_id": connected["workspace_session_id"]},
    )
    assert heartbeat.status_code == 400


@pytest.mark.asyncio
async def test_workspace_client_permission_validation(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    repository, branch, conversation = await _setup(client, workspace)
    connected = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )

    other = await create_workspace(client, second_user, name="Other WS")
    forbidden = await client.post(
        "/workspace-client/heartbeat",
        headers=other.headers,
        json={"workspace_session_id": connected["workspace_session_id"]},
    )
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_workspace_client_invalid_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    response = await client.post(
        "/workspace-client/connect",
        headers=workspace.headers,
        json={
            "repository_id": str(uuid4()),
            "repository_branch_id": str(uuid4()),
            "conversation_id": conversation["id"],
            "client_name": "vscode",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_client_invalid_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])
    response = await client.post(
        "/workspace-client/connect",
        headers=workspace.headers,
        json={
            "repository_id": repository["id"],
            "repository_branch_id": branch["id"],
            "conversation_id": str(uuid4()),
            "client_name": "vscode",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_client_multiple_simultaneous_sessions(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    member_ws = WorkspaceContext(
        workspace_id=workspace.workspace_id,
        headers=member_headers,
        auth=second_user,
    )

    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])

    conv1 = await _create_conversation(client, workspace, project_id=project_id, title="One")
    await _enable_and_attach(
        client, workspace, conversation_id=conv1["id"], repository_id=repository["id"]
    )
    conv2 = await _create_conversation(client, member_ws, project_id=project_id, title="Two")
    await _enable_and_attach(
        client, member_ws, conversation_id=conv2["id"], repository_id=repository["id"]
    )

    s1 = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conv1["id"],
        client_name="vscode",
    )
    s2 = await _connect(
        client,
        member_ws,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conv2["id"],
        client_name="cursor",
    )
    assert s1["workspace_session_id"] != s2["workspace_session_id"]

    status = await client.get(
        f"/repositories/{repository['id']}/workspace-client/status",
        headers=workspace.headers,
    )
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["plugin_protocol_ready"] is True
    assert body["connected_sessions"] >= 2
