"""Tests for Sprint 18 — branch manager and commit graph visualization."""

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


@pytest.mark.asyncio
async def test_branch_manager_returns_tree_and_status(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace, "Root")
    message = await _post_message(client, workspace, root["id"], "seed")
    await _commit(client, workspace, root["id"], message["id"], "Root commit")

    branch = await client.post(
        f"/conversations/{root['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Feature A"},
    )
    assert branch.status_code == 201
    branch_id = branch.json()["id"]
    branch_message = await _post_message(client, workspace, branch_id, "branch work")
    await _commit(client, workspace, branch_id, branch_message["id"], "Feature commit")

    response = await client.get(
        f"/conversations/{branch_id}/branch-manager",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["root"]["id"] == root["id"]
    assert body["total_branches"] >= 2
    assert body["total_commits"] >= 2
    child = next(item for item in body["root"]["children"] if item["id"] == branch_id)
    assert child["branch_name"] == "Feature A"
    assert child["commit_count"] == 1
    assert child["commits_ahead"] == 1
    assert child["is_owned_by_viewer"] is True


@pytest.mark.asyncio
async def test_commit_graph_nodes_and_edges(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    first = await _post_message(client, workspace, conversation["id"], "one")
    second = await _post_message(client, workspace, conversation["id"], "two")
    first_commit = await _commit(client, workspace, conversation["id"], first["id"], "One")
    second_commit = await _commit(client, workspace, conversation["id"], second["id"], "Two")

    response = await client.get(
        f"/conversations/{conversation['id']}/commit-graph",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    body = response.json()
    hashes = {node["commit_hash"] for node in body["nodes"]}
    assert first_commit["commit_hash"] in hashes
    assert second_commit["commit_hash"] in hashes
    assert any(
        edge["source"] == first_commit["commit_hash"]
        and edge["target"] == second_commit["commit_hash"]
        for edge in body["edges"]
    )


@pytest.mark.asyncio
async def test_family_overview_aggregates(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, root["id"], "seed")
    await _commit(client, workspace, root["id"], message["id"], "Root")
    branch = await client.post(
        f"/conversations/{root['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Alt"},
    )
    assert branch.status_code == 201

    response = await client.get(
        f"/conversations/{root['id']}/family-overview",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_branches"] >= 2
    assert body["total_commits"] >= 1
    assert body["total_messages"] >= 1
    assert body["credits_used"] is not None


@pytest.mark.asyncio
async def test_commit_search_by_title_and_author(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "needle in haystack")
    await _commit(client, workspace, conversation["id"], message["id"], "Authentication Complete")

    by_title = await client.get(
        f"/conversations/{conversation['id']}/commits/search",
        headers=workspace.headers,
        params={"q": "authentication"},
    )
    assert by_title.status_code == 200
    assert any(item["title"] == "Authentication Complete" for item in by_title.json()["results"])

    by_message = await client.get(
        f"/conversations/{conversation['id']}/commits/search",
        headers=workspace.headers,
        params={"q": "needle"},
    )
    assert by_message.status_code == 200
    assert len(by_message.json()["results"]) >= 1

    by_author = await client.get(
        f"/conversations/{conversation['id']}/commits/search",
        headers=workspace.headers,
        params={"author": workspace.auth.name[:4]},
    )
    assert by_author.status_code == 200
    assert len(by_author.json()["results"]) >= 1
