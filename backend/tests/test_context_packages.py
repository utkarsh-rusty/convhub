"""Tests for Sprint 19 — Context Packages."""

from __future__ import annotations

from uuid import uuid4

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
async def test_context_package_created_after_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "hello world")
    commit = await _commit(client, workspace, conversation["id"], message["id"], "First milestone")

    assert commit["context_package_id"] is not None

    package = await client.get(
        f"/context-packages/{commit['context_package_id']}",
        headers=workspace.headers,
    )
    assert package.status_code == 200
    body = package.json()
    assert body["commit_id"] == commit["id"]
    assert body["conversation_id"] == conversation["id"]
    assert body["status"] == "generated"
    assert body["version"] == 1
    assert body["metadata"]["commit"]["commit_hash"] == commit["commit_hash"]
    assert body["statistics"]["message_count"] >= 1
    assert "first" in body["search_keywords"] or "milestone" in body["search_keywords"]
    assert body["summary"]["architecture_notes"] == []
    assert body["summary"]["decisions"] == []
    assert body["summary"]["todos"] == []


@pytest.mark.asyncio
async def test_one_package_per_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "once")
    commit = await _commit(client, workspace, conversation["id"], message["id"], "Once")

    by_commit = await client.get(
        f"/commits/{commit['id']}/context-package",
        headers=workspace.headers,
    )
    assert by_commit.status_code == 200
    assert by_commit.json()["id"] == commit["context_package_id"]

    listed = await client.get(
        f"/conversations/{conversation['id']}/context-packages",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_rollback_if_package_generation_fails(
    client: AsyncClient,
    workspace: WorkspaceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "fail me")

    async def boom(*args, **kwargs):
        raise RuntimeError("package generation failed")

    monkeypatch.setattr(
        "app.conversations.context_packages.ContextPackageService.generate_for_commit",
        boom,
    )

    response = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "Should roll back", "latest_message_id": message["id"]},
    )
    assert response.status_code == 500

    commits = await client.get(
        f"/conversations/{conversation['id']}/commits",
        headers=workspace.headers,
    )
    assert commits.status_code == 200
    assert commits.json() == []


@pytest.mark.asyncio
async def test_export_endpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "exportable")
    commit = await _commit(client, workspace, conversation["id"], message["id"], "Export me")

    exported = await client.get(
        f"/context-packages/{commit['context_package_id']}/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200
    body = exported.json()
    assert body["id"] == commit["context_package_id"]
    assert "metadata" in body
    assert "summary" in body
    assert "statistics" in body
    assert "search_keywords" in body


@pytest.mark.asyncio
async def test_package_is_immutable_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "snapshot")
    commit = await _commit(client, workspace, conversation["id"], message["id"], "Snapshot")

    first = await client.get(
        f"/context-packages/{commit['context_package_id']}",
        headers=workspace.headers,
    )
    assert first.status_code == 200
    first_body = first.json()

    await _post_message(client, workspace, conversation["id"], "after package")

    second = await client.get(
        f"/context-packages/{commit['context_package_id']}",
        headers=workspace.headers,
    )
    assert second.status_code == 200
    assert second.json()["statistics"] == first_body["statistics"]
    assert second.json()["metadata"] == first_body["metadata"]


@pytest.mark.asyncio
async def test_branch_commits_generate_separate_packages(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    root = await _create_conversation(client, workspace, "Root")
    message = await _post_message(client, workspace, root["id"], "seed")
    root_commit = await _commit(client, workspace, root["id"], message["id"], "Root commit")

    branch = await client.post(
        f"/conversations/{root['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Experiment"},
    )
    assert branch.status_code == 201
    branch_id = branch.json()["id"]
    branch_message = await _post_message(client, workspace, branch_id, "branch only")
    branch_commit = await _commit(
        client, workspace, branch_id, branch_message["id"], "Branch commit"
    )

    assert root_commit["context_package_id"] != branch_commit["context_package_id"]

    root_packages = await client.get(
        f"/conversations/{root['id']}/context-packages",
        headers=workspace.headers,
    )
    branch_packages = await client.get(
        f"/conversations/{branch_id}/context-packages",
        headers=workspace.headers,
    )
    assert len(root_packages.json()) == 1
    assert len(branch_packages.json()) == 1


@pytest.mark.asyncio
async def test_statistics_and_credits_included(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    first = await _post_message(client, workspace, conversation["id"], "one")
    await _post_message(client, workspace, conversation["id"], "two")
    commit = await _commit(client, workspace, conversation["id"], first["id"], "Stats")

    package = await client.get(
        f"/context-packages/{commit['context_package_id']}",
        headers=workspace.headers,
    )
    stats = package.json()["statistics"]
    assert stats["message_count"] >= 1
    assert stats["participant_count"] >= 1
    assert "credits_used" in stats
    assert stats["borrowed_requests"] == 0
    assert isinstance(stats["providers_used"], list)


@pytest.mark.asyncio
async def test_package_not_found_for_other_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    from tests.conftest import register_user

    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "private")
    commit = await _commit(client, workspace, conversation["id"], message["id"], "Private")

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
        f"/context-packages/{commit['context_package_id']}",
        headers=other_headers,
    )
    assert response.status_code == 404
