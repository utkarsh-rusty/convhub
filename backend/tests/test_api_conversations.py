"""Conversation, participant, and message API QA tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    AuthContext,
    WorkspaceContext,
    invite_and_accept,
    register_user,
)


async def _create_conversation(
    client: AsyncClient, workspace: WorkspaceContext, title: str = "QA Chat"
):
    response = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_conversation_crud_happy_path(
    client: AsyncClient, workspace: WorkspaceContext
) -> None:
    created = await _create_conversation(client, workspace, "Planning")
    conv_id = created["id"]

    listed = await client.get("/conversations", headers=workspace.headers)
    assert listed.status_code == 200
    assert any(item["id"] == conv_id for item in listed.json())

    detail = await client.get(f"/conversations/{conv_id}", headers=workspace.headers)
    assert detail.status_code == 200
    assert detail.json()["title"] == "Planning"

    updated = await client.patch(
        f"/conversations/{conv_id}",
        headers=workspace.headers,
        json={"title": "Renamed"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"

    deleted = await client.delete(f"/conversations/{conv_id}", headers=workspace.headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_conversations_require_workspace_header(
    client: AsyncClient,
    auth_user: AuthContext,
) -> None:
    response = await client.get("/conversations", headers=auth_user.headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_participant_cannot_access_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    created = await _create_conversation(client, workspace)
    outsider_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    response = await client.get(
        f"/conversations/{created['id']}",
        headers=outsider_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_archive_and_restore_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await _create_conversation(client, workspace)
    conv_id = created["id"]

    archived = await client.post(f"/conversations/{conv_id}/archive", headers=workspace.headers)
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    listed = await client.get("/conversations", headers=workspace.headers)
    assert all(item["id"] != conv_id for item in listed.json())

    restored = await client.post(f"/conversations/{conv_id}/restore", headers=workspace.headers)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_participant_management(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    created = await _create_conversation(client, workspace)
    conv_id = created["id"]

    added = await client.post(
        f"/conversations/{conv_id}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    assert added.status_code == 201
    assert len(added.json()) == 2

    listed = await client.get(
        f"/conversations/{conv_id}/participants",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    user_ids = [participant["user_id"] for participant in listed.json()]
    assert second_user.user_id in user_ids

    removed = await client.delete(
        f"/conversations/{conv_id}/participants/{second_user.user_id}",
        headers=workspace.headers,
    )
    assert removed.status_code == 204


@pytest.mark.asyncio
async def test_member_cannot_add_participants(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    created = await _create_conversation(client, workspace)
    member_headers = {**second_user.headers, "X-Workspace-ID": workspace.workspace_id}

    await client.post(
        f"/conversations/{created['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )

    third = await register_user(client, email=f"third-{uuid4().hex}@example.com")
    await invite_and_accept(client, workspace, third)

    response = await client.post(
        f"/conversations/{created['id']}/participants",
        headers=member_headers,
        json={"user_ids": [third.user_id]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_remove_conversation_owner(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await _create_conversation(client, workspace)
    response = await client.delete(
        f"/conversations/{created['id']}/participants/{workspace.auth.user_id}",
        headers=workspace.headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_message_create_and_list(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await _create_conversation(client, workspace)
    conv_id = created["id"]

    message = await client.post(
        f"/conversations/{conv_id}/messages",
        headers=workspace.headers,
        json={"content": "Hello team", "role": "user"},
    )
    assert message.status_code == 201
    assert message.json()["content"] == "Hello team"

    messages = await client.get(f"/conversations/{conv_id}/messages", headers=workspace.headers)
    assert messages.status_code == 200
    assert len(messages.json()) == 1


@pytest.mark.asyncio
async def test_message_rejects_empty_content(
    client: AsyncClient, workspace: WorkspaceContext
) -> None:
    created = await _create_conversation(client, workspace)
    response = await client.post(
        f"/conversations/{created['id']}/messages",
        headers=workspace.headers,
        json={"content": "", "role": "user"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_message_rejects_assistant_role_via_api(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    created = await _create_conversation(client, workspace)
    response = await client.post(
        f"/conversations/{created['id']}/messages",
        headers=workspace.headers,
        json={"content": "Should fail", "role": "assistant"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_participant_returns_409(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    created = await _create_conversation(client, workspace)
    payload = {"user_ids": [second_user.user_id]}
    first = await client.post(
        f"/conversations/{created['id']}/participants",
        headers=workspace.headers,
        json=payload,
    )
    assert first.status_code == 201
    second = await client.post(
        f"/conversations/{created['id']}/participants",
        headers=workspace.headers,
        json=payload,
    )
    assert second.status_code == 409
