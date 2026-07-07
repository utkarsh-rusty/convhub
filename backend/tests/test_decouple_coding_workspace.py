"""Tests for Sprint 25 — Decouple coding workspace from repository."""

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
async def test_enable_coding_without_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    body = await _enable_coding(client, workspace, conversation_id=conversation["id"])

    assert body["coding_enabled"] is True
    assert body["repository_id"] is None
    assert body["repository"] is None


@pytest.mark.asyncio
async def test_attach_existing_repository_later(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    attached = await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    assert attached["coding_enabled"] is True
    assert attached["repository_id"] == repository["id"]
    assert attached["repository"]["name"] == repository["name"]


@pytest.mark.asyncio
async def test_create_repository_while_attaching(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_coding(client, workspace, conversation_id=conversation["id"])

    attached = await client.post(
        f"/conversations/{conversation['id']}/attach-repository",
        headers=workspace.headers,
        json={
            "create_repository": {
                "name": "Mobile App",
                "provider": "gitlab",
                "owner": "convhub",
                "repository_name": "mobile",
                "remote_url": "https://gitlab.com/convhub/mobile",
                "default_branch": "main",
                "visibility": "private",
            }
        },
    )
    assert attached.status_code == 200, attached.text
    body = attached.json()
    assert body["coding_enabled"] is True
    assert body["repository_id"] is not None
    assert body["repository"]["name"] == "Mobile App"


@pytest.mark.asyncio
async def test_detach_repository_keeps_coding_enabled(
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
    assert detached.status_code == 200, detached.text
    body = detached.json()
    assert body["coding_enabled"] is True
    assert body["repository_id"] is None
    assert body["repository"] is None


@pytest.mark.asyncio
async def test_branch_memory_created_only_after_repository_attachment(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await _enable_coding(client, workspace, conversation_id=conversation["id"])

    listed_before = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    assert listed_before.status_code == 200
    assert listed_before.json() == []

    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    listed_after = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    assert listed_after.status_code == 200
    branches = listed_after.json()
    assert len(branches) == 1
    assert branches[0]["name"] == "main"
    assert branches[0]["memory"] is not None


@pytest.mark.asyncio
async def test_repository_branch_created_only_after_repository_attachment(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    listed_before = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    assert listed_before.status_code == 200
    assert listed_before.json() == []

    await _enable_coding(client, workspace, conversation_id=conversation["id"])
    await _attach_repository(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    listed_after = await client.get(
        f"/repositories/{repository['id']}/branches",
        headers=workspace.headers,
    )
    assert listed_after.status_code == 200
    assert len(listed_after.json()) == 1


@pytest.mark.asyncio
async def test_existing_conversation_can_become_coding_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id, title="Legacy")

    assert conversation["coding_enabled"] is False

    body = await _enable_coding(client, workspace, conversation_id=conversation["id"])
    assert body["coding_enabled"] is True
    assert body["title"] == "Legacy"


@pytest.mark.asyncio
async def test_repository_apis_remain_compatible(
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

    listed = await client.get(
        f"/repositories/{repository['id']}/conversations",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == conversation["id"] for item in listed.json())

    detail = await client.get(f"/repositories/{repository['id']}", headers=workspace.headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == repository["id"]
