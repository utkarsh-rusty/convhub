"""Tests for Sprint 26 — Branch Sync History."""

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


async def _create_branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    name: str = "main",
) -> dict:
    response = await client.post(
        f"/repositories/{repository_id}/branches",
        headers=workspace.headers,
        json={"name": name, "is_default": True},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_branch_sync_record_created_on_memory_init(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])

    history = await client.get(
        f"/repository-branches/{branch['id']}/history",
        headers=workspace.headers,
    )
    assert history.status_code == 200
    records = history.json()
    assert len(records) == 1
    assert records[0]["sync_type"] == "attach_repository"
    assert records[0]["sync_version"] == 1


@pytest.mark.asyncio
async def test_branch_sync_records_are_immutable(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])

    history = await client.get(
        f"/repository-branches/{branch['id']}/history",
        headers=workspace.headers,
    )
    record_id = history.json()[0]["id"]

    patch = await client.patch(
        f"/branch-sync-records/{record_id}",
        headers=workspace.headers,
        json={"notes": "changed"},
    )
    assert patch.status_code in {404, 405}

    delete = await client.delete(
        f"/branch-sync-records/{record_id}",
        headers=workspace.headers,
    )
    assert delete.status_code in {404, 405}


@pytest.mark.asyncio
async def test_branch_memory_latest_pointer_updates(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    branch_id = branches.json()[0]["id"]
    memory = await client.get(
        f"/repository-branches/{branch_id}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["latest_sync_record_id"] is not None
    assert body["memory_version"] >= 2
    assert body["latest_sync_record"]["sync_type"] == "attach_repository"


@pytest.mark.asyncio
async def test_attach_repository_creates_sync_record(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    branch_id = branches.json()[0]["id"]
    history = await client.get(
        f"/repository-branches/{branch_id}/history",
        headers=workspace.headers,
    )
    attach_records = [item for item in history.json() if item["sync_type"] == "attach_repository"]
    assert len(attach_records) >= 1
    assert any(item["conversation_id"] == conversation["id"] for item in attach_records)


@pytest.mark.asyncio
async def test_detach_repository_creates_sync_record(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    detached = await client.post(
        f"/conversations/{conversation['id']}/detach-repository",
        headers=workspace.headers,
    )
    assert detached.status_code == 200

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    branch_id = branches.json()[0]["id"]
    history = await client.get(
        f"/repository-branches/{branch_id}/history",
        headers=workspace.headers,
    )
    assert history.json()[0]["sync_type"] == "detach_repository"


@pytest.mark.asyncio
async def test_commit_creates_sync_record(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    message = await _post_message(client, workspace, conversation["id"], "Ship it")
    commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"latest_message_id": message["id"], "title": "Checkpoint"},
    )
    assert commit.status_code == 201, commit.text

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    branch_id = branches.json()[0]["id"]
    history = await client.get(
        f"/repository-branches/{branch_id}/history",
        headers=workspace.headers,
    )
    assert history.json()[0]["sync_type"] == "local_commit"
    assert history.json()[0]["commit_id"] is not None


@pytest.mark.asyncio
async def test_restore_creates_sync_record(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    message = await _post_message(client, workspace, conversation["id"], "Restore me")
    commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"latest_message_id": message["id"], "title": "Before restore"},
    )
    assert commit.status_code == 201
    package_id = commit.json()["context_package_id"]

    restored = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Restored workspace"},
    )
    assert restored.status_code == 201, restored.text

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    branch_id = branches.json()[0]["id"]
    history = await client.get(
        f"/repository-branches/{branch_id}/history",
        headers=workspace.headers,
    )
    assert history.json()[0]["sync_type"] == "restore"


@pytest.mark.asyncio
async def test_history_export_endpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])

    exported = await client.get(
        f"/repository-branches/{branch['id']}/history/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200
    body = exported.json()
    assert body["filename"] == "branch-history.json"
    assert body["content"]["repository_branch_id"] == branch["id"]
    assert isinstance(body["content"]["records"], list)
    assert "messages" not in body["content"]


@pytest.mark.asyncio
async def test_get_branch_sync_record_endpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(client, workspace, repository_id=repository["id"])

    history = await client.get(
        f"/repository-branches/{branch['id']}/history",
        headers=workspace.headers,
    )
    record_id = history.json()[0]["id"]
    detail = await client.get(
        f"/branch-sync-records/{record_id}",
        headers=workspace.headers,
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == record_id
    assert detail.json()["repository_branch_id"] == branch["id"]
