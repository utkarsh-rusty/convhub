"""Tests for Sprint 16 — branch visualization and comparison."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import WorkspaceContext


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


async def _branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
    conversation_id: str,
    message_id: str,
    branch_name: str,
) -> dict:
    response = await client.post(
        f"/conversations/{conversation_id}/branch",
        headers=workspace.headers,
        json={"message_id": message_id, "branch_name": branch_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_conversation_response_includes_branch_metadata(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Meta")
    await _post_message(client, workspace, conversation["id"], "hello")

    detail = await client.get(
        f"/conversations/{conversation['id']}",
        headers=workspace.headers,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["owner_name"] == workspace.auth.name
    assert body["created_by_name"] == workspace.auth.name
    assert body["latest_activity_at"] == body["last_activity_at"]
    assert body["message_count"] == 1
    assert body["ai_request_count"] == 0
    assert body["participant_count"] == 1


@pytest.mark.asyncio
async def test_branch_tree_returns_hierarchy(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace, "Root")
    first = await _post_message(client, workspace, root["id"], "one")
    await _post_message(client, workspace, root["id"], "two")
    branch_a = await _branch(client, workspace, root["id"], first["id"], "A")
    branch_message = await _post_message(client, workspace, branch_a["id"], "a-only")
    branch_b = await _branch(client, workspace, branch_a["id"], branch_message["id"], "B")

    response = await client.get(
        f"/conversations/{branch_b['id']}/branch-tree",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    tree = response.json()
    assert tree["root"]["id"] == root["id"]
    assert tree["root"]["owner_name"] == workspace.auth.name
    assert tree["root"]["message_count"] == 2
    child_names = {child["branch_name"] for child in tree["root"]["children"]}
    assert "A" in child_names
    branch_a_node = next(child for child in tree["root"]["children"] if child["branch_name"] == "A")
    assert any(child["id"] == branch_b["id"] for child in branch_a_node["children"])


@pytest.mark.asyncio
async def test_compare_identifies_shared_and_divergent_messages(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace, "Compare Root")
    shared_one = await _post_message(client, workspace, root["id"], "shared-1")
    await _post_message(client, workspace, root["id"], "shared-2")
    left = await _branch(client, workspace, root["id"], shared_one["id"], "Left")
    right = await _branch(client, workspace, root["id"], shared_one["id"], "Right")

    await _post_message(client, workspace, left["id"], "left-only")
    await _post_message(client, workspace, right["id"], "right-only")

    response = await client.get(
        f"/conversations/{left['id']}/compare/{right['id']}",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["common_ancestor_id"] == root["id"]
    assert [message["content"] for message in body["shared_messages"]] == ["shared-1"]
    assert [message["content"] for message in body["left_only"]] == ["left-only"]
    assert [message["content"] for message in body["right_only"]] == ["right-only"]
    assert body["divergence_message_id"] == body["shared_messages"][-1]["id"]


@pytest.mark.asyncio
async def test_timeline_uses_existing_metadata(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace, "Timeline Root")
    message = await _post_message(client, workspace, root["id"], "seed")
    branch = await _branch(client, workspace, root["id"], message["id"], "Experiment")

    response = await client.get(
        f"/conversations/{branch['id']}/timeline",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    events = response.json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "ConversationCreated" in event_types
    assert "ConversationBranched" in event_types
    assert "ParticipantsAdded" in event_types
    assert events == sorted(events, key=lambda event: event["occurred_at"])


@pytest.mark.asyncio
async def test_stats_are_accurate(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Stats")
    await _post_message(client, workspace, conversation["id"], "one")
    await _post_message(client, workspace, conversation["id"], "two")

    response = await client.get(
        f"/conversations/{conversation['id']}/stats",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message_count"] == 2
    assert body["user_messages"] == 2
    assert body["assistant_messages"] == 0
    assert body["participants"] == 1
    assert body["providers_used"] == []
    assert body["borrowed_requests"] == 0
    assert body["credits_used"] in {"0", "0.0", "0.000000"}
    assert body["latest_activity"] is not None


@pytest.mark.asyncio
async def test_search_returns_matching_messages_with_context(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Search")
    await _post_message(client, workspace, conversation["id"], "alpha")
    target = await _post_message(client, workspace, conversation["id"], "find the needle here")
    await _post_message(client, workspace, conversation["id"], "omega")

    response = await client.get(
        f"/conversations/{conversation['id']}/search",
        headers=workspace.headers,
        params={"q": "needle"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "needle"
    assert len(body["matches"]) == 1
    match = body["matches"][0]
    assert match["message"]["id"] == target["id"]
    assert [item["content"] for item in match["context_before"]] == ["alpha"]
    assert [item["content"] for item in match["context_after"]] == ["omega"]


@pytest.mark.asyncio
async def test_search_empty_query_returns_no_matches(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace, "Empty Search")
    await _post_message(client, workspace, conversation["id"], "hello")
    response = await client.get(
        f"/conversations/{conversation['id']}/search",
        headers=workspace.headers,
        params={"q": "   "},
    )
    assert response.status_code == 200
    assert response.json()["matches"] == []
