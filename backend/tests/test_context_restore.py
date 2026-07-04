"""Tests for Sprint 20 — Context Restore (Project Checkpoints)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import AuthContext, WorkspaceContext, invite_and_accept, register_user


async def _create_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
    title: str = "Main",
) -> dict:
    response = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": title},
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


async def _commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
    conversation_id: str,
    message_id: str,
    title: str,
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/commit",
        headers=workspace.headers,
        json={"title": title, "latest_message_id": message_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _package_for_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
    commit: dict,
) -> dict:
    response = await client.get(
        f"/context-packages/{commit['context_package_id']}",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_restore_creates_new_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace, "Original")
    message = await _post_message(client, workspace, original["id"], "checkpoint message")
    commit = await _commit(client, workspace, original["id"], message["id"], "Checkpoint A")
    package = await _package_for_commit(client, workspace, commit)

    restored = await client.post(
        f"/context-packages/{package['id']}/restore",
        headers=workspace.headers,
        json={
            "conversation_name": "Restored Working Copy",
            "restore_participants": True,
            "restore_messages": True,
            "restore_metadata": True,
            "restore_only_self": False,
        },
    )
    assert restored.status_code == 201, restored.text
    body = restored.json()
    assert body["id"] != original["id"]
    assert body["title"] == "Restored Working Copy"
    assert body["is_restored"] is True
    assert body["restored_from_package_id"] == package["id"]
    assert body["restored_from_commit_id"] == commit["id"]
    assert body["restored_from_conversation_id"] == original["id"]
    assert body["restored_by_user_id"] == workspace.auth.user_id
    assert body["restored_from_commit_hash"] == commit["commit_hash"]
    assert body["owner_id"] == workspace.auth.user_id


@pytest.mark.asyncio
async def test_original_conversation_and_package_unchanged(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace, "Stable")
    message = await _post_message(client, workspace, original["id"], "stable message")
    commit = await _commit(client, workspace, original["id"], message["id"], "Stable commit")
    package_before = await _package_for_commit(client, workspace, commit)

    await client.post(
        f"/context-packages/{package_before['id']}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Copy"},
    )

    original_after = await client.get(
        f"/conversations/{original['id']}",
        headers=workspace.headers,
    )
    assert original_after.status_code == 200
    assert original_after.json()["title"] == "Stable"
    assert original_after.json()["is_restored"] is False

    messages = await client.get(
        f"/conversations/{original['id']}/messages",
        headers=workspace.headers,
    )
    assert len(messages.json()) == 1

    package_after = await _package_for_commit(client, workspace, commit)
    assert package_after["statistics"] == package_before["statistics"]
    assert package_after["metadata"] == package_before["metadata"]


@pytest.mark.asyncio
async def test_participants_restored_and_only_self(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    original = await _create_conversation(client, workspace, "Team")
    await client.post(
        f"/conversations/{original['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    message = await _post_message(client, workspace, original["id"], "team note")
    commit = await _commit(client, workspace, original["id"], message["id"], "Team checkpoint")
    package_id = commit["context_package_id"]

    all_participants = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={
            "conversation_name": "All participants",
            "restore_participants": True,
            "restore_only_self": False,
            "restore_messages": False,
        },
    )
    assert all_participants.status_code == 201
    all_ids = {p["user_id"] for p in all_participants.json()["participants"]}
    assert workspace.auth.user_id in all_ids
    assert second_user.user_id in all_ids

    only_self = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={
            "conversation_name": "Only me",
            "restore_participants": True,
            "restore_only_self": True,
            "restore_messages": False,
        },
    )
    assert only_self.status_code == 201
    self_ids = {p["user_id"] for p in only_self.json()["participants"]}
    assert self_ids == {workspace.auth.user_id}


@pytest.mark.asyncio
async def test_messages_and_metadata_restored(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace, "Source")
    first = await _post_message(client, workspace, original["id"], "first")
    branch = await client.post(
        f"/conversations/{original['id']}/branch",
        headers=workspace.headers,
        json={"message_id": first["id"], "branch_name": "experiment"},
    )
    assert branch.status_code == 201, branch.text
    branch_id = branch.json()["id"]
    second = await _post_message(client, workspace, branch_id, "second")
    commit = await _commit(client, workspace, branch_id, second["id"], "Both messages")

    restored = await client.post(
        f"/context-packages/{commit['context_package_id']}/restore",
        headers=workspace.headers,
        json={
            "conversation_name": "With messages",
            "restore_messages": True,
            "restore_metadata": True,
        },
    )
    assert restored.status_code == 201
    body = restored.json()
    conversation_id = body["id"]
    assert body["branch_name"] == "experiment"
    assert body["parent_conversation_id"] is None

    messages = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=workspace.headers,
    )
    assert messages.status_code == 200
    contents = [item["content"] for item in messages.json()]
    assert contents == ["first", "second"]


@pytest.mark.asyncio
async def test_multiple_restores_from_same_package(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, original["id"], "seed")
    commit = await _commit(client, workspace, original["id"], message["id"], "Seed")
    package_id = commit["context_package_id"]

    first = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Restore 1"},
    )
    second = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Restore 2"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["restored_from_package_id"] == package_id
    assert second.json()["restored_from_package_id"] == package_id


@pytest.mark.asyncio
async def test_restore_lineage_endpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace, "Lineage Source")
    message = await _post_message(client, workspace, original["id"], "lineage")
    commit = await _commit(client, workspace, original["id"], message["id"], "Lineage commit")
    restored = await client.post(
        f"/context-packages/{commit['context_package_id']}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Lineage copy"},
    )
    conversation_id = restored.json()["id"]

    info = await client.get(
        f"/conversations/{conversation_id}/restore-info",
        headers=workspace.headers,
    )
    assert info.status_code == 200
    body = info.json()
    assert body["is_restored"] is True
    assert body["original_conversation_id"] == original["id"]
    assert body["original_conversation_title"] == "Lineage Source"
    assert body["original_commit_id"] == commit["id"]
    assert body["original_commit_hash"] == commit["commit_hash"]
    assert body["context_package_id"] == commit["context_package_id"]
    assert body["restored_by_user_id"] == workspace.auth.user_id


@pytest.mark.asyncio
async def test_restore_info_not_found_for_normal_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    response = await client.get(
        f"/conversations/{conversation['id']}/restore-info",
        headers=workspace.headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_restore_permission_enforcement(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    original = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, original["id"], "private")
    commit = await _commit(client, workspace, original["id"], message["id"], "Private")

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
    response = await client.post(
        f"/context-packages/{commit['context_package_id']}/restore",
        headers=other_headers,
        json={"conversation_name": "Nope"},
    )
    assert response.status_code == 404
