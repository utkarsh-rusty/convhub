"""Tests for Sprint 32 — Transcript Snapshot Engine."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import WorkspaceContext, create_workspace, register_user


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
            "repository_name": name.lower().replace(" ", "-"),
            "remote_url": f"https://github.com/convhub/{name.lower().replace(' ', '-')}",
            "default_branch": "main",
            "visibility": "private",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    name: str,
    is_default: bool = False,
) -> dict:
    response = await client.post(
        f"/repositories/{repository_id}/branches",
        headers=workspace.headers,
        json={"name": name, "is_default": is_default},
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


async def _setup_repo(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> tuple[dict, dict, dict]:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client,
        workspace,
        repository_id=repository["id"],
        name="main",
        is_default=True,
    )
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    return repository, branch, conversation


async def _connect(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    repository_branch_id: str,
    conversation_id: str | None = None,
    provider: str = "claude_code",
    machine_identifier: str = "macbook-dev-1",
) -> dict:
    payload: dict = {
        "provider": provider,
        "repository_id": repository_id,
        "repository_branch_id": repository_branch_id,
        "machine_identifier": machine_identifier,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    response = await client.post(
        "/external-ai-sessions/connect",
        headers=workspace.headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _upload(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    session_id: str,
    sequence_number: int,
    start_offset: int,
    end_offset: int,
    raw_content: str,
) -> dict:
    response = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session_id,
            "sequence_number": sequence_number,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "raw_content": raw_content,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _get_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
    session_id: str,
) -> dict:
    response = await client.get(
        f"/external-ai-sessions/{session_id}/snapshot",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_empty_transcript_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    snapshot = await _get_snapshot(client, workspace, session["id"])
    assert snapshot["external_ai_session_id"] == session["id"]
    assert snapshot["snapshot_version"] == 1
    assert snapshot["character_count"] == 0

    exported = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert body["content"] == ""
    assert body["character_count"] == 0
    assert body["filename"].endswith(".md")
    assert "content" not in snapshot


@pytest.mark.asyncio
async def test_single_chunk_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=5,
        raw_content="hello",
    )
    snapshot = await _get_snapshot(client, workspace, session["id"])
    assert snapshot["snapshot_version"] == 2
    assert snapshot["character_count"] == 5

    exported = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200
    assert exported.json()["content"] == "hello"


@pytest.mark.asyncio
async def test_multiple_ordered_chunks_and_regeneration(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    empty = await _get_snapshot(client, workspace, session["id"])
    assert empty["snapshot_version"] == 1
    assert empty["character_count"] == 0

    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=5,
        raw_content="hello",
    )
    after_first = await _get_snapshot(client, workspace, session["id"])
    assert after_first["snapshot_version"] == 2
    assert after_first["character_count"] == 5

    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=2,
        start_offset=5,
        end_offset=11,
        raw_content=" world",
    )
    after_second = await _get_snapshot(client, workspace, session["id"])
    assert after_second["snapshot_version"] == 3
    assert after_second["character_count"] == 11

    exported = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot/export",
        headers=workspace.headers,
    )
    assert exported.status_code == 200
    assert exported.json()["content"] == "hello world"
    assert exported.json()["snapshot_version"] == 3


@pytest.mark.asyncio
async def test_append_only_snapshot_grows(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=3,
        raw_content="abc",
    )
    first = await _get_snapshot(client, workspace, session["id"])
    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=2,
        start_offset=3,
        end_offset=6,
        raw_content="def",
    )
    second = await _get_snapshot(client, workspace, session["id"])
    assert second["snapshot_version"] > first["snapshot_version"]
    assert second["character_count"] == first["character_count"] + 3

    exported = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot/export",
        headers=workspace.headers,
    )
    assert exported.json()["content"] == "abcdef"


@pytest.mark.asyncio
async def test_snapshot_export_permissions(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=4,
        raw_content="perm",
    )

    outsider = await register_user(client, name="Outsider")
    other_ws = await create_workspace(client, outsider)

    forbidden_get = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot",
        headers=other_ws.headers,
    )
    assert forbidden_get.status_code == 404

    forbidden_export = await client.get(
        f"/external-ai-sessions/{session['id']}/snapshot/export",
        headers=other_ws.headers,
    )
    assert forbidden_export.status_code == 404

    missing = await client.get(
        f"/external-ai-sessions/{uuid4()}/snapshot",
        headers=workspace.headers,
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_snapshot_repository_isolation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repo_a = await _create_repository(client, workspace, project_id=project_id, name="Repo A")
    repo_b = await _create_repository(client, workspace, project_id=project_id, name="Repo B")
    branch_a = await _create_branch(
        client, workspace, repository_id=repo_a["id"], name="main", is_default=True
    )
    branch_b = await _create_branch(
        client, workspace, repository_id=repo_b["id"], name="main", is_default=True
    )
    conversation = await _create_conversation(client, workspace, project_id=project_id)

    session_a = await _connect(
        client,
        workspace,
        repository_id=repo_a["id"],
        repository_branch_id=branch_a["id"],
        conversation_id=conversation["id"],
        machine_identifier="machine-a",
    )
    session_b = await _connect(
        client,
        workspace,
        repository_id=repo_b["id"],
        repository_branch_id=branch_b["id"],
        conversation_id=conversation["id"],
        machine_identifier="machine-b",
    )
    await _upload(
        client,
        workspace,
        session_id=session_a["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=4,
        raw_content="aaaa",
    )
    await _upload(
        client,
        workspace,
        session_id=session_b["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=4,
        raw_content="bbbb",
    )

    export_a = await client.get(
        f"/external-ai-sessions/{session_a['id']}/snapshot/export",
        headers=workspace.headers,
    )
    export_b = await client.get(
        f"/external-ai-sessions/{session_b['id']}/snapshot/export",
        headers=workspace.headers,
    )
    assert export_a.status_code == 200
    assert export_b.status_code == 200
    assert export_a.json()["content"] == "aaaa"
    assert export_b.json()["content"] == "bbbb"
    assert export_a.json()["content"] != export_b.json()["content"]


@pytest.mark.asyncio
async def test_reconnect_ensures_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    first = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    snapshot_before = await _get_snapshot(client, workspace, first["id"])
    second = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    assert second["id"] == first["id"]
    snapshot_after = await _get_snapshot(client, workspace, second["id"])
    assert snapshot_after["id"] == snapshot_before["id"]
    assert snapshot_after["snapshot_version"] == snapshot_before["snapshot_version"]
