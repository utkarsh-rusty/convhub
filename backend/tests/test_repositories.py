"""Tests for Sprint 22 — Repository integration and coding conversations."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import AuthContext, WorkspaceContext, invite_and_accept, register_user


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


@pytest.mark.asyncio
async def test_repository_crud_and_list_by_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    created = await _create_repository(client, workspace, project_id=project_id)
    repository_id = created["id"]

    assert created["name"] == "ConvHub API"
    assert created["provider"] == "github"
    assert created["default_branch"] == "main"
    assert created["sync_status"] == "not_synced"
    assert created["latest_commit"] is None

    updated = await client.patch(
        f"/repositories/{repository_id}",
        headers=workspace.headers,
        json={"name": "API Repo", "default_branch": "develop"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "API Repo"
    assert updated.json()["default_branch"] == "develop"

    listed = await client.get(
        f"/projects/{project_id}/repositories",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == repository_id

    archived = await client.post(
        f"/repositories/{repository_id}/archive",
        headers=workspace.headers,
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert archived.json()["is_active"] is False

    restored = await client.post(
        f"/repositories/{repository_id}/restore",
        headers=workspace.headers,
    )
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert restored.json()["is_active"] is True

    deleted = await client.delete(f"/repositories/{repository_id}", headers=workspace.headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_cannot_delete_repository_with_connected_conversations(
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

    blocked = await client.delete(
        f"/repositories/{repository['id']}",
        headers=workspace.headers,
    )
    assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_existing_conversations_default_without_coding(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Legacy"},
    )
    assert conversation.status_code == 201
    body = conversation.json()
    assert body["coding_enabled"] is False
    assert body["repository_id"] is None
    assert body["repository"] is None


@pytest.mark.asyncio
async def test_cannot_attach_repository_without_coding_enabled(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    response = await client.post(
        f"/conversations/{conversation['id']}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository["id"]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_attach_repository_after_enable_coding(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    enabled = await _enable_coding(client, workspace, conversation_id=conversation["id"])
    assert enabled["coding_enabled"] is True
    assert enabled["repository_id"] is None

    body = await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    assert body["coding_enabled"] is True
    assert body["repository_id"] == repository["id"]
    assert body["repository"]["name"] == repository["name"]
    assert body["repository"]["sync_status"] == "not_synced"


@pytest.mark.asyncio
async def test_attach_and_detach_repository_on_coding_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    enabled = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert enabled.status_code == 200
    conversation_id = enabled.json()["id"]

    attached = await client.post(
        f"/conversations/{conversation_id}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository["id"]},
    )
    assert attached.status_code == 200
    assert attached.json()["repository_id"] == repository["id"]

    detached = await client.post(
        f"/conversations/{conversation_id}/detach-repository",
        headers=workspace.headers,
    )
    assert detached.status_code == 200
    assert detached.json()["repository_id"] is None
    assert detached.json()["repository"] is None


@pytest.mark.asyncio
async def test_multiple_coding_conversations_share_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)

    first = await _create_conversation(client, workspace, project_id=project_id, title="First")
    second = await _create_conversation(client, workspace, project_id=project_id, title="Second")
    for conversation in (first, second):
        await _enable_coding(client, workspace, conversation_id=conversation["id"])
        await _attach_repository(
            client,
            workspace,
            conversation_id=conversation["id"],
            repository_id=repository["id"],
        )

    listed = await client.get(
        f"/repositories/{repository['id']}/conversations",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert ids == {first["id"], second["id"]}


@pytest.mark.asyncio
async def test_repository_must_match_conversation_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_a = await _create_project(client, workspace, name="A")
    project_b = await _create_project(client, workspace, name="B")
    repository = await _create_repository(client, workspace, project_id=project_a)
    conversation = await _create_conversation(client, workspace, project_id=project_b)

    enabled = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert enabled.status_code == 200

    attach = await client.post(
        f"/conversations/{conversation['id']}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository["id"]},
    )
    assert attach.status_code == 400


@pytest.mark.asyncio
async def test_repository_permissions_require_workspace_membership(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)

    outsider = await register_user(client, email=f"outsider-{uuid4().hex}@example.com")
    other = await client.post(
        "/workspaces",
        headers=outsider.headers,
        json={"name": "Other"},
    )
    other_headers = {
        **outsider.headers,
        "X-Workspace-ID": other.json()["id"],
    }

    response = await client.get(
        f"/repositories/{repository['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_member_can_list_repositories(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    project_id = await _create_project(client, workspace)
    await _create_repository(client, workspace, project_id=project_id)

    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    response = await client.get("/repositories", headers=member_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
