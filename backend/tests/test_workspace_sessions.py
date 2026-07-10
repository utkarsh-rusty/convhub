"""Tests for Sprint 28 — Developer Workspace Sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import create_engine
from tests.conftest import AuthContext, WorkspaceContext, create_workspace, invite_and_accept, register_user


async def _create_project(client: AsyncClient, workspace: WorkspaceContext, name: str = "Backend") -> str:
    response = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    project_id: str,
    name: str = "ConvHub API",
) -> dict:
    response = await client.post(
        "/repositories",
        headers=workspace.headers,
        json={
            "project_id": project_id,
            "name": name,
            "provider": "github",
            "owner": "convhub",
            "repository_name": name.lower().replace(" ", "-"),
            "remote_url": f"https://github.com/convhub/{name.lower().replace(' ', '-')}",
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
    name: str,
    is_default: bool = False,
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
    title: str = "Discussion",
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


async def _create_session(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    repository_branch_id: str,
    conversation_id: str,
    client_name: str = "vscode",
    platform: str = "darwin",
) -> dict:
    response = await client.post(
        "/workspace-sessions",
        headers=workspace.headers,
        json={
            "repository_id": repository_id,
            "repository_branch_id": repository_branch_id,
            "conversation_id": conversation_id,
            "client_name": client_name,
            "client_version": "1.0.0",
            "platform": platform,
            "working_directory": "/tmp/project",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _set_last_heartbeat(session_id: str, when: datetime) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    UPDATE developer_workspace_sessions
                    SET last_heartbeat_at = :when
                    WHERE id = :session_id
                    """
                ),
                {"when": when, "session_id": session_id},
            )
    finally:
        await engine.dispose()


async def _setup_repo_session(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> tuple[dict, dict, dict, dict]:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="main",
        is_default=True,
    )
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    return repository, branch, conversation, {"project_id": project_id}


@pytest.mark.asyncio
async def test_create_workspace_session(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    assert session["status"] == "active"
    assert session["repository_id"] == repository["id"]
    assert session["repository_branch_id"] == branch["id"]
    assert session["conversation_id"] == conversation["id"]
    assert session["user_id"] == workspace.auth.user_id
    assert session["client_name"] == "vscode"
    assert session["platform"] == "darwin"
    assert session["closed_at"] is None


@pytest.mark.asyncio
async def test_heartbeat_updates_timestamp(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    before = session["last_heartbeat_at"]

    await _set_last_heartbeat(
        session["id"],
        datetime.now(UTC) - timedelta(minutes=2),
    )

    response = await client.post(
        f"/workspace-sessions/{session['id']}/heartbeat",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "active"
    assert body["last_heartbeat_at"] != before
    assert body["last_heartbeat_at"] > before


@pytest.mark.asyncio
async def test_close_session(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )

    response = await client.post(
        f"/workspace-sessions/{session['id']}/close",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "closed"
    assert body["closed_at"] is not None

    listed = await client.get(
        f"/repositories/{repository['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []


@pytest.mark.asyncio
async def test_list_active_sessions(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )

    response = await client.get(
        f"/repositories/{repository['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["status"] == "active"
    assert sessions[0]["user_name"] is not None
    assert sessions[0]["repository_branch_name"] == "main"


@pytest.mark.asyncio
async def test_idle_transition(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _set_last_heartbeat(session["id"], datetime.now(UTC) - timedelta(minutes=6))

    response = await client.post(
        "/workspace-sessions/mark-idle",
        headers=workspace.headers,
        params={"idle_after_seconds": 300, "disconnected_after_seconds": 900},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert len(updated) == 1
    assert updated[0]["status"] == "idle"

    detail = await client.get(
        f"/workspace-sessions/{session['id']}",
        headers=workspace.headers,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "idle"


@pytest.mark.asyncio
async def test_disconnected_transition(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _set_last_heartbeat(session["id"], datetime.now(UTC) - timedelta(minutes=20))

    response = await client.post(
        "/workspace-sessions/mark-idle",
        headers=workspace.headers,
        params={"idle_after_seconds": 300, "disconnected_after_seconds": 900},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert len(updated) == 1
    assert updated[0]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_multiple_developers(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    member_workspace = WorkspaceContext(
        workspace_id=workspace.workspace_id,
        headers=member_headers,
        auth=second_user,
    )

    repository, branch, conversation, meta = await _setup_repo_session(client, workspace)
    conversation_b = await _create_conversation(
        client,
        member_workspace,
        project_id=meta["project_id"],
        title="Second developer",
    )
    await _enable_and_attach(
        client,
        member_workspace,
        conversation_id=conversation_b["id"],
        repository_id=repository["id"],
    )

    await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        client_name="cursor",
    )
    await _create_session(
        client,
        member_workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation_b["id"],
        client_name="vscode",
    )

    response = await client.get(
        f"/repositories/{repository['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    user_ids = {item["user_id"] for item in sessions}
    assert user_ids == {workspace.auth.user_id, second_user.user_id}


@pytest.mark.asyncio
async def test_multiple_repository_branches(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, main_branch, conversation, meta = await _setup_repo_session(client, workspace)
    feature_branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="feature",
        is_default=False,
    )
    conversation_b = await _create_conversation(
        client,
        workspace,
        project_id=meta["project_id"],
        title="Feature work",
    )
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation_b["id"],
        repository_id=repository["id"],
    )

    await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=main_branch["id"],
        conversation_id=conversation["id"],
    )
    await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=feature_branch["id"],
        conversation_id=conversation_b["id"],
    )

    response = await client.get(
        f"/repositories/{repository['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    branch_names = {item["repository_branch_name"] for item in sessions}
    assert branch_names == {"main", "feature"}


@pytest.mark.asyncio
async def test_repository_isolation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repo_a = await _create_repository(client, workspace, project_id=project_id, name="Repo A")
    repo_b = await _create_repository(client, workspace, project_id=project_id, name="Repo B")
    branch_a = await _create_branch(
        client, workspace, repository_id=repo_a["id"], name="main", is_default=True
    )
    branch_b = await _create_branch(
        client, workspace, repository_id=repo_b["id"], name="main", is_default=True
    )
    conversation_a = await _create_conversation(client, workspace, project_id=project_id, title="A")
    conversation_b = await _create_conversation(client, workspace, project_id=project_id, title="B")
    await _enable_and_attach(
        client, workspace, conversation_id=conversation_a["id"], repository_id=repo_a["id"]
    )
    await _enable_and_attach(
        client, workspace, conversation_id=conversation_b["id"], repository_id=repo_b["id"]
    )

    await _create_session(
        client,
        workspace,
        repository_id=repo_a["id"],
        repository_branch_id=branch_a["id"],
        conversation_id=conversation_a["id"],
    )
    await _create_session(
        client,
        workspace,
        repository_id=repo_b["id"],
        repository_branch_id=branch_b["id"],
        conversation_id=conversation_b["id"],
    )

    listed_a = await client.get(
        f"/repositories/{repo_a['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    listed_b = await client.get(
        f"/repositories/{repo_b['id']}/workspace-sessions",
        headers=workspace.headers,
    )
    assert listed_a.status_code == 200
    assert listed_b.status_code == 200
    assert len(listed_a.json()) == 1
    assert len(listed_b.json()) == 1
    assert listed_a.json()[0]["repository_id"] == repo_a["id"]
    assert listed_b.json()[0]["repository_id"] == repo_b["id"]


@pytest.mark.asyncio
async def test_permission_checks(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    repository, branch, conversation, _ = await _setup_repo_session(client, workspace)
    session = await _create_session(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )

    other_workspace = await create_workspace(client, second_user, name="Other")
    forbidden_get = await client.get(
        f"/workspace-sessions/{session['id']}",
        headers=other_workspace.headers,
    )
    assert forbidden_get.status_code == 404

    forbidden_list = await client.get(
        f"/repositories/{repository['id']}/workspace-sessions",
        headers=other_workspace.headers,
    )
    assert forbidden_list.status_code == 404

    missing = await client.get(
        f"/workspace-sessions/{uuid4()}",
        headers=workspace.headers,
    )
    assert missing.status_code == 404

    detail = await client.get(
        f"/workspace-sessions/{session['id']}",
        headers=workspace.headers,
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == session["id"]
