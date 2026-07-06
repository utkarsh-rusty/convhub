"""Tests for Sprint 21 — Projects."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import AuthContext, WorkspaceContext, invite_and_accept, register_user


@pytest.mark.asyncio
async def test_workspace_creates_default_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    response = await client.get("/projects", headers=workspace.headers)
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["name"] == "Default Project"
    assert projects[0]["is_default"] is True


@pytest.mark.asyncio
async def test_create_and_update_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await client.post(
        "/projects",
        headers=workspace.headers,
        json={
            "name": "Backend",
            "description": "API work",
            "icon": "box",
            "color": "#3b82f6",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Backend"
    assert body["description"] == "API work"
    assert body["icon"] == "box"
    assert body["color"] == "#3b82f6"
    assert body["created_by_id"] == workspace.auth.user_id

    updated = await client.patch(
        f"/projects/{body['id']}",
        headers=workspace.headers,
        json={"name": "Backend API", "description": "Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Backend API"
    assert updated.json()["description"] == "Updated"


@pytest.mark.asyncio
async def test_archive_and_restore_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Research"},
    )
    project_id = created.json()["id"]

    archived = await client.post(
        f"/projects/{project_id}/archive",
        headers=workspace.headers,
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    listed = await client.get("/projects", headers=workspace.headers)
    assert all(item["id"] != project_id for item in listed.json())

    restored = await client.post(
        f"/projects/{project_id}/restore",
        headers=workspace.headers,
    )
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_delete_empty_project_and_block_non_empty(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    empty = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Empty"},
    )
    empty_id = empty.json()["id"]

    deleted = await client.delete(f"/projects/{empty_id}", headers=workspace.headers)
    assert deleted.status_code == 204

    project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "With Conversations"},
    )
    project_id = project.json()["id"]
    conversation = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Inside", "project_id": project_id},
    )
    assert conversation.status_code == 201
    assert conversation.json()["project_id"] == project_id

    blocked = await client.delete(f"/projects/{project_id}", headers=workspace.headers)
    assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_conversation_belongs_to_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Frontend"},
    )
    project_id = project.json()["id"]

    conversation = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "UI work", "project_id": project_id},
    )
    assert conversation.status_code == 201
    body = conversation.json()
    assert body["project_id"] == project_id

    listed = await client.get(
        f"/projects/{project_id}/conversations",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_default_project_used_when_project_id_omitted(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    projects = await client.get("/projects", headers=workspace.headers)
    default_id = projects.json()[0]["id"]

    conversation = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Default home"},
    )
    assert conversation.status_code == 201
    assert conversation.json()["project_id"] == default_id


@pytest.mark.asyncio
async def test_project_overview_details(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Overview", "description": "Repo-like home"},
    )
    project_id = project.json()["id"]
    await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Recent", "project_id": project_id},
    )

    detail = await client.get(f"/projects/{project_id}", headers=workspace.headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["conversation_count"] == 1
    assert body["description"] == "Repo-like home"
    assert len(body["members"]) >= 1
    assert len(body["recent_conversations"]) == 1


@pytest.mark.asyncio
async def test_restore_into_original_and_other_project(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original_project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Original"},
    )
    other_project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Other"},
    )
    original_id = original_project.json()["id"]
    other_id = other_project.json()["id"]

    conversation = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Source", "project_id": original_id},
    )
    conversation_id = conversation.json()["id"]
    message = await client.post(
        f"/conversations/{conversation_id}/messages",
        headers=workspace.headers,
        json={"content": "checkpoint", "role": "user"},
    )
    commit = await client.post(
        f"/conversations/{conversation_id}/commit",
        headers=workspace.headers,
        json={"title": "CP", "latest_message_id": message.json()["id"]},
    )
    package_id = commit.json()["context_package_id"]

    default_restore = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Same project"},
    )
    assert default_restore.status_code == 201
    assert default_restore.json()["project_id"] == original_id

    other_restore = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Moved", "project_id": other_id},
    )
    assert other_restore.status_code == 201
    assert other_restore.json()["project_id"] == other_id


@pytest.mark.asyncio
async def test_project_permissions_require_workspace_membership(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project = await client.post(
        "/projects",
        headers=workspace.headers,
        json={"name": "Private"},
    )
    project_id = project.json()["id"]

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
    response = await client.get(f"/projects/{project_id}", headers=other_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_member_can_list_projects(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    response = await client.get("/projects", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
