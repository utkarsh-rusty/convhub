"""Tests for Sprint 15 — conversation branching MVP."""

from __future__ import annotations

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
    client: AsyncClient,
    workspace: WorkspaceContext,
    title: str = "Main thread",
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


@pytest.mark.asyncio
async def test_branch_creation_copies_messages_and_sets_creator_as_sole_owner(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace, "Roadmap")
    conv_id = conversation["id"]

    add_participants = await client.post(
        f"/conversations/{conv_id}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    assert add_participants.status_code == 201

    await _post_message(client, workspace, conv_id, "Hello")
    second = await _post_message(client, workspace, conv_id, "Second message")
    third = await _post_message(client, workspace, conv_id, "Third message")

    branch_response = await client.post(
        f"/conversations/{conv_id}/branch",
        headers=workspace.headers,
        json={"message_id": second["id"], "branch_name": "Experiment A"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()

    assert branch["parent_conversation_id"] == conv_id
    assert branch["branch_from_message_id"] == second["id"]
    assert branch["branch_name"] == "Experiment A"
    assert branch["workspace_id"] == workspace.workspace_id
    assert branch["id"] != conv_id
    assert branch["owner_id"] == workspace.auth.user_id
    assert branch["owner"]["user_id"] == workspace.auth.user_id

    branch_messages = await client.get(
        f"/conversations/{branch['id']}/messages",
        headers=workspace.headers,
    )
    assert branch_messages.status_code == 200
    branch_contents = [message["content"] for message in branch_messages.json()]
    assert branch_contents == ["Hello", "Second message"]
    assert "Third message" not in branch_contents
    assert third["id"] not in {message["id"] for message in branch_messages.json()}

    branch_participants = await client.get(
        f"/conversations/{branch['id']}/participants",
        headers=workspace.headers,
    )
    assert branch_participants.status_code == 200
    branch_user_ids = {p["user_id"] for p in branch_participants.json()}
    assert branch_user_ids == {workspace.auth.user_id}
    assert second_user.user_id not in branch_user_ids

    parent_participants = await client.get(
        f"/conversations/{conv_id}/participants",
        headers=workspace.headers,
    )
    assert parent_participants.status_code == 200
    parent_user_ids = {p["user_id"] for p in parent_participants.json()}
    assert parent_user_ids == {workspace.auth.user_id, second_user.user_id}

    parent_messages = await client.get(
        f"/conversations/{conv_id}/messages",
        headers=workspace.headers,
    )
    assert parent_messages.status_code == 200
    assert len(parent_messages.json()) == 3


@pytest.mark.asyncio
async def test_branch_creation_from_first_message_copies_only_one(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    first = await _post_message(client, workspace, conversation["id"], "one")
    await _post_message(client, workspace, conversation["id"], "two")

    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": first["id"]},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()

    branch_messages = await client.get(
        f"/conversations/{branch['id']}/messages",
        headers=workspace.headers,
    )
    contents = [m["content"] for m in branch_messages.json()]
    assert contents == ["one"]


@pytest.mark.asyncio
async def test_branch_rejects_invalid_message_id(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)

    response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": str(uuid4()), "branch_name": "Nope"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_branch_rejects_message_from_other_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation_a = await _create_conversation(client, workspace, "Thread A")
    conversation_b = await _create_conversation(client, workspace, "Thread B")
    message_b = await _post_message(client, workspace, conversation_b["id"], "b message")

    response = await client.post(
        f"/conversations/{conversation_a['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message_b["id"], "branch_name": "cross"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_branch_requires_conversation_access(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "hi")

    outsider_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }

    response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=outsider_headers,
        json={"message_id": message["id"], "branch_name": "no"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_branches_returns_child_conversations(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "hi")

    for name in ("Branch A", "Branch B"):
        response = await client.post(
            f"/conversations/{conversation['id']}/branch",
            headers=workspace.headers,
            json={"message_id": message["id"], "branch_name": name},
        )
        assert response.status_code == 201, response.text

    branches_response = await client.get(
        f"/conversations/{conversation['id']}/branches",
        headers=workspace.headers,
    )
    assert branches_response.status_code == 200
    branches = branches_response.json()
    assert len(branches) == 2
    branch_names = sorted(b["branch_name"] for b in branches)
    assert branch_names == ["Branch A", "Branch B"]
    for branch in branches:
        assert branch["parent_conversation_id"] == conversation["id"]


@pytest.mark.asyncio
async def test_lineage_endpoint_returns_root_and_current(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Root")
    message = await _post_message(client, workspace, conversation["id"], "hi")

    first_branch = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Layer 1"},
    )
    assert first_branch.status_code == 201, first_branch.text
    first_branch_data = first_branch.json()

    branch_message = await _post_message(
        client, workspace, first_branch_data["id"], "branch message"
    )
    nested_branch = await client.post(
        f"/conversations/{first_branch_data['id']}/branch",
        headers=workspace.headers,
        json={"message_id": branch_message["id"], "branch_name": "Layer 2"},
    )
    assert nested_branch.status_code == 201, nested_branch.text
    nested_data = nested_branch.json()

    lineage_response = await client.get(
        f"/conversations/{nested_data['id']}/lineage",
        headers=workspace.headers,
    )
    assert lineage_response.status_code == 200
    lineage = lineage_response.json()
    assert lineage["root"]["id"] == conversation["id"]
    assert lineage["current"]["id"] == nested_data["id"]
    ancestor_ids = [item["id"] for item in lineage["ancestors"]]
    assert ancestor_ids == [first_branch_data["id"]]


@pytest.mark.asyncio
async def test_lineage_root_conversation_returns_self(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Solo")
    lineage_response = await client.get(
        f"/conversations/{conversation['id']}/lineage",
        headers=workspace.headers,
    )
    assert lineage_response.status_code == 200
    lineage = lineage_response.json()
    assert lineage["root"]["id"] == conversation["id"]
    assert lineage["current"]["id"] == conversation["id"]
    assert lineage["ancestors"] == []


@pytest.mark.asyncio
async def test_conversation_list_sidebar_data_includes_branch_metadata(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Main")
    message = await _post_message(client, workspace, conversation["id"], "hi")

    branch = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Side"},
    )
    assert branch.status_code == 201, branch.text
    branch_data = branch.json()

    listed = await client.get("/conversations", headers=workspace.headers)
    assert listed.status_code == 200

    items = {item["id"]: item for item in listed.json()}
    assert conversation["id"] in items
    assert branch_data["id"] in items

    main_item = items[conversation["id"]]
    branch_item = items[branch_data["id"]]

    assert main_item["parent_conversation_id"] is None
    assert main_item.get("branch_name") in (None, "")
    assert branch_item["parent_conversation_id"] == conversation["id"]
    assert branch_item["branch_name"] == "Side"
    assert branch_item["branch_from_message_id"] == message["id"]


@pytest.mark.asyncio
async def test_branch_from_workspace_outsider_returns_403(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "hi")

    outsider = await register_user(client, email=f"outsider-{uuid4().hex}@example.com")
    outsider_headers = {
        **outsider.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=outsider_headers,
        json={"message_id": message["id"], "branch_name": "no"},
    )
    assert response.status_code == 403
