"""Tests for Sprint 24 — Branch Memory foundation."""

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
    default_branch: str = "main",
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
            "default_branch": default_branch,
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
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert response.status_code == 200, response.text
    return response.json()


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


@pytest.mark.asyncio
async def test_repository_branch_crud(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)

    listed = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []

    main_branch = await client.post(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
        json={"name": "main", "is_default": True},
    )
    assert main_branch.status_code == 201, main_branch.text
    branches = [main_branch.json()]
    assert branches[0]["name"] == "main"
    assert branches[0]["is_default"] is True
    assert branches[0]["memory"] is not None

    created = await client.post(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
        json={"name": "develop"},
    )
    assert created.status_code == 201, created.text
    branch = created.json()
    assert branch["name"] == "develop"
    assert branch["memory"] is not None

    renamed = await client.patch(
        f"/repository-branches/{branch['id']}",
        headers=workspace.headers,
        json={"name": "development"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "development"

    archived = await client.post(
        f"/repository-branches/{branch['id']}/archive",
        headers=workspace.headers,
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    restored = await client.post(
        f"/repository-branches/{branch['id']}/restore",
        headers=workspace.headers,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True

    archived_again = await client.post(
        f"/repository-branches/{branch['id']}/archive",
        headers=workspace.headers,
    )
    assert archived_again.status_code == 200

    deleted = await client.delete(
        f"/repository-branches/{branch['id']}",
        headers=workspace.headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_one_branch_memory_per_repository_branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)

    created = await client.post(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
        json={"name": "feature/login"},
    )
    branch_id = created.json()["id"]

    memory = await client.get(
        f"/repository-branches/{branch_id}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["repository_branch_id"] == branch_id
    assert body["memory_version"] == 1
    assert body["sync_status"] == "not_synced"


@pytest.mark.asyncio
async def test_branch_memory_updates_after_repository_attachment(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    attached = await client.post(
        f"/conversations/{conversation['id']}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository["id"]},
    )
    assert attached.status_code == 200

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    default_branch = next(item for item in branches.json() if item["is_default"])
    memory = await client.get(
        f"/repository-branches/{default_branch['id']}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["current_conversation_id"] == conversation["id"]
    assert body["memory_version"] >= 2


@pytest.mark.asyncio
async def test_branch_memory_updates_after_commit_and_package(
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
    message = await _post_message(client, workspace, conversation["id"], "Implement auth")

    commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={
            "latest_message_id": message["id"],
            "title": "Auth checkpoint",
            "description": "Initial auth work",
        },
    )
    assert commit.status_code == 201, commit.text
    commit_body = commit.json()

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    default_branch = next(item for item in branches.json() if item["is_default"])
    memory = await client.get(
        f"/repository-branches/{default_branch['id']}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["current_commit_id"] is not None
    assert body["current_commit_hash"] == commit_body["commit_hash"]
    assert body["current_context_package_id"] is not None
    assert body["current_context_package_version"] is not None


@pytest.mark.asyncio
async def test_branch_memory_updates_after_restore(
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
    assert package_id is not None

    restored = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Restored branch memory"},
    )
    assert restored.status_code == 201, restored.text
    restored_body = restored.json()

    branches = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    default_branch = next(item for item in branches.json() if item["is_default"])
    memory = await client.get(
        f"/repository-branches/{default_branch['id']}/memory",
        headers=workspace.headers,
    )
    assert memory.status_code == 200
    body = memory.json()
    assert body["current_conversation_id"] == restored_body["id"]
    assert body["current_context_package_id"] == package_id


@pytest.mark.asyncio
async def test_branch_memory_export_endpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    created = await client.post(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
        json={"name": "main", "is_default": True},
    )
    assert created.status_code == 201, created.text
    branch_id = created.json()["id"]

    exported = await client.get(
        f"/repository-branches/{branch_id}/memory/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200
    body = exported.json()
    assert body["filename"] == "branch-memory.json"
    assert body["content"]["repository_branch_id"] == branch_id
    assert body["content"]["sync_status"] == "not_synced"
    assert "messages" not in body["content"]
