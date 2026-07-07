"""Tests for Sprint 23 — Coding workspace refactor."""

from __future__ import annotations

from uuid import uuid4

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


@pytest.mark.asyncio
async def test_new_conversations_start_without_coding(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    assert conversation["coding_enabled"] is False
    assert conversation["repository_id"] is None
    assert conversation["repository"] is None


@pytest.mark.asyncio
async def test_enable_coding_with_existing_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    enabled = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={"existing_repository_id": repository["id"]},
    )
    assert enabled.status_code == 200, enabled.text
    body = enabled.json()
    assert body["coding_enabled"] is True
    assert body["repository_id"] == repository["id"]
    assert body["repository"]["name"] == repository["name"]


@pytest.mark.asyncio
async def test_enable_coding_with_create_repository_payload(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    enabled = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
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
    assert enabled.status_code == 200, enabled.text
    body = enabled.json()
    assert body["coding_enabled"] is True
    assert body["repository_id"] is not None
    assert body["repository"]["name"] == "Mobile App"


@pytest.mark.asyncio
async def test_disable_coding_detaches_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={"existing_repository_id": repository["id"]},
    )

    disabled = await client.post(
        f"/conversations/{conversation['id']}/disable-coding",
        headers=workspace.headers,
    )
    assert disabled.status_code == 200, disabled.text
    body = disabled.json()
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

    attach = await client.post(
        f"/conversations/{conversation['id']}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository["id"]},
    )
    assert attach.status_code == 400


@pytest.mark.asyncio
async def test_branch_inherits_repository_and_can_detach(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    parent = await _create_conversation(client, workspace, project_id=project_id, title="Parent")

    await client.post(
        f"/conversations/{parent['id']}/enable-coding",
        headers=workspace.headers,
        json={"existing_repository_id": repository["id"]},
    )

    message = await client.post(
        f"/conversations/{parent['id']}/messages",
        headers=workspace.headers,
        json={"content": "Branch point", "role": "user"},
    )
    assert message.status_code == 201

    branch = await client.post(
        f"/conversations/{parent['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message.json()["id"], "branch_name": "experiment"},
    )
    assert branch.status_code == 201, branch.text
    branch_body = branch.json()
    assert branch_body["coding_enabled"] is True
    assert branch_body["repository_id"] == repository["id"]

    detached = await client.post(
        f"/conversations/{branch_body['id']}/detach-repository",
        headers=workspace.headers,
    )
    assert detached.status_code == 200
    assert detached.json()["repository_id"] is None
    assert detached.json()["coding_enabled"] is True


@pytest.mark.asyncio
async def test_branch_can_attach_different_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    first_repo = await _create_repository(client, workspace, project_id=project_id, name="First")
    second_repo = await _create_repository(
        client,
        workspace,
        project_id=project_id,
        name="Second",
    )
    parent = await _create_conversation(client, workspace, project_id=project_id, title="Parent")

    await client.post(
        f"/conversations/{parent['id']}/enable-coding",
        headers=workspace.headers,
        json={"existing_repository_id": first_repo["id"]},
    )

    message = await client.post(
        f"/conversations/{parent['id']}/messages",
        headers=workspace.headers,
        json={"content": "Branch point", "role": "user"},
    )
    assert message.status_code == 201

    branch = await client.post(
        f"/conversations/{parent['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message.json()["id"], "branch_name": "other-repo"},
    )
    assert branch.status_code == 201
    branch_id = branch.json()["id"]

    detached = await client.post(
        f"/conversations/{branch_id}/detach-repository",
        headers=workspace.headers,
    )
    assert detached.status_code == 200

    attached = await client.post(
        f"/conversations/{branch_id}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": second_repo["id"]},
    )
    assert attached.status_code == 200
    assert attached.json()["repository_id"] == second_repo["id"]


@pytest.mark.asyncio
async def test_enable_coding_is_idempotent_guarded(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    first = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_migration_preserves_repository_links(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    enabled = await client.post(
        f"/conversations/{conversation['id']}/enable-coding",
        headers=workspace.headers,
        json={"existing_repository_id": repository["id"]},
    )
    assert enabled.status_code == 200

    listed = await client.get(
        f"/repositories/{repository['id']}/conversations",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == conversation["id"] for item in listed.json())


@pytest.mark.asyncio
async def test_multiple_conversations_share_repository_after_enable(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    first = await _create_conversation(client, workspace, project_id=project_id, title="First")
    second = await _create_conversation(client, workspace, project_id=project_id, title="Second")

    for conversation in (first, second):
        response = await client.post(
            f"/conversations/{conversation['id']}/enable-coding",
            headers=workspace.headers,
            json={"existing_repository_id": repository["id"]},
        )
        assert response.status_code == 200
        assert response.json()["repository_id"] == repository["id"]

    listed = await client.get(
        f"/repositories/{repository['id']}/conversations",
        headers=workspace.headers,
    )
    ids = {item["id"] for item in listed.json()}
    assert ids == {first["id"], second["id"]}
