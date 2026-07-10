"""Tests for Sprint 27 — Sync API Foundation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import WorkspaceContext


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
            "repository_name": "api",
            "remote_url": "https://github.com/convhub/api",
            "default_branch": "main",
            "visibility": "private",
        },
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


async def _enable_coding(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
) -> None:
    response = await client.post(
        f"/conversations/{conversation_id}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert response.status_code == 200, response.text


async def _attach_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
    repository_id: str,
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository_id},
    )
    assert response.status_code == 200, response.text
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


async def _post_message(
    client: AsyncClient,
    workspace: WorkspaceContext,
    conversation_id: str,
    content: str,
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/messages",
        headers=workspace.headers,
        json={"content": content, "role": "user"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
    latest_message_id: str,
    title: str = "Checkpoint",
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/commit",
        headers=workspace.headers,
        json={"latest_message_id": latest_message_id, "title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_sync_version_increments_on_sync_record_creation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="main",
        is_default=True,
    )

    memory = await client.get(
        f"/repository-branches/{branch['id']}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["current_sync_version"] == 1
    assert body["memory_version"] == 1

    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    memory = await client.get(
        f"/repository-branches/{branch['id']}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["current_sync_version"] == 2
    assert body["memory_version"] == 2


@pytest.mark.asyncio
async def test_sync_push_registration(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    message = await _post_message(client, workspace, conversation["id"], "Hello sync")
    commit = await _create_commit(
        client,
        workspace,
        conversation_id=conversation["id"],
        latest_message_id=message["id"],
    )

    response = await client.post(
        "/sync/push",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
        json={"notes": "Plugin push"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sync_version"] == 4
    assert body["sync_state"] == "synced"
    assert body["latest_sync_record"]["sync_type"] == "plugin_push"
    assert body["latest_sync_record"]["commit_id"] == commit["id"]
    assert body["last_synchronized_at"] is not None

    history = await client.get(
        f"/repository-branches/{branch['id']}/history",
        headers=workspace.headers,
    )
    assert history.status_code == 200
    records = history.json()
    assert records[0]["sync_type"] == "plugin_push"
    assert records[0]["notes"] == "Plugin push"


@pytest.mark.asyncio
async def test_sync_pull_metadata(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    response = await client.get(
        "/sync/pull",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["branch_sync_version"] == 2
    assert body["branch_memory"]["repository_branch_id"] == branch["id"]
    assert body["latest_sync_record"]["sync_type"] == "attach_repository"
    assert body["latest_commit"] is None
    assert body["latest_context_package"] is None


@pytest.mark.asyncio
async def test_sync_status_calculation_ahead(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    message = await _post_message(client, workspace, conversation["id"], "New work")
    await _create_commit(
        client,
        workspace,
        conversation_id=conversation["id"],
        latest_message_id=message["id"],
    )
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    response = await client.get(
        "/sync/status",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sync_state"] == "ahead"
    assert body["latest_commit"] is None
    assert body["repository"]["id"] == repository["id"]
    assert body["repository_branch"]["id"] == branch["id"]


@pytest.mark.asyncio
async def test_sync_status_detached_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    detach = await client.post(
        f"/conversations/{conversation['id']}/detach-repository",
        headers=workspace.headers,
    )
    assert detach.status_code == 200, detach.text

    response = await client.get(
        "/sync/status",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["sync_state"] == "detached"


@pytest.mark.asyncio
async def test_sync_status_without_commits(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    response = await client.get(
        "/sync/status",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sync_state"] == "synced"
    assert body["latest_commit"] is None
    assert body["latest_context_package"] is None


@pytest.mark.asyncio
async def test_sync_with_multiple_branches(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    main_branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="main",
        is_default=True,
    )
    feature_branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="feature",
        is_default=False,
    )

    main_status = await client.get(
        "/sync/status",
        headers=workspace.headers,
        params={"repository_branch_id": main_branch["id"]},
    )
    feature_status = await client.get(
        "/sync/status",
        headers=workspace.headers,
        params={"repository_branch_id": feature_branch["id"]},
    )
    assert main_status.status_code == 200
    assert feature_status.status_code == 200
    assert main_status.json()["repository_branch"]["name"] == "main"
    assert feature_status.json()["repository_branch"]["name"] == "feature"
    assert main_status.json()["sync_version"] == 1
    assert feature_status.json()["sync_version"] == 1


@pytest.mark.asyncio
async def test_sync_push_rejected_when_detached(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
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
    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    await client.post(
        f"/conversations/{conversation['id']}/detach-repository",
        headers=workspace.headers,
    )

    response = await client.post(
        "/sync/push",
        headers=workspace.headers,
        params={"repository_branch_id": branch["id"]},
        json={},
    )
    assert response.status_code == 400
