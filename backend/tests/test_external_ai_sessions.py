"""Tests for Sprint 31 — External AI Session Foundation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    AuthContext,
    WorkspaceContext,
    create_workspace,
    invite_and_accept,
    register_user,
)


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


@pytest.mark.asyncio
async def test_create_external_ai_session(
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
    assert session["provider"] == "claude_code"
    assert session["status"] == "active"
    assert session["repository_id"] == repository["id"]
    assert session["repository_branch_id"] == branch["id"]
    assert session["conversation_id"] == conversation["id"]
    assert session["workspace_user_id"] == workspace.auth.user_id
    assert session["machine_identifier"] == "macbook-dev-1"
    assert session["last_synced_offset"] == 0
    assert session["chunk_count"] == 0
    assert session["ended_at"] is None
    assert session["developer_name"] == workspace.auth.name
    assert session["repository_branch_name"] == "main"


@pytest.mark.asyncio
async def test_reconnect_resumes_active_session(
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
    second = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    assert second["id"] == first["id"]
    assert second["status"] == "active"


@pytest.mark.asyncio
async def test_append_chunks_ordering_and_offsets(
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

    chunk1 = await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=10,
        raw_content="hello",
    )
    chunk2 = await _upload(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=2,
        start_offset=10,
        end_offset=25,
        raw_content=" world",
    )

    assert chunk1["sequence_number"] == 1
    assert chunk2["sequence_number"] == 2

    detail = await client.get(
        f"/external-ai-sessions/{session['id']}",
        headers=workspace.headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["last_synced_offset"] == 25
    assert detail.json()["chunk_count"] == 2

    chunks = await client.get(
        f"/external-ai-sessions/{session['id']}/chunks",
        headers=workspace.headers,
    )
    assert chunks.status_code == 200, chunks.text
    body = chunks.json()
    assert [c["sequence_number"] for c in body] == [1, 2]
    assert [c["raw_content"] for c in body] == ["hello", " world"]
    assert body[0]["start_offset"] == 0
    assert body[0]["end_offset"] == 10
    assert body[1]["start_offset"] == 10
    assert body[1]["end_offset"] == 25


@pytest.mark.asyncio
async def test_append_rejects_bad_sequence_and_offsets(
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
        raw_content="a",
    )

    bad_sequence = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session["id"],
            "sequence_number": 3,
            "start_offset": 5,
            "end_offset": 10,
            "raw_content": "b",
        },
    )
    assert bad_sequence.status_code == 409

    bad_offset = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session["id"],
            "sequence_number": 2,
            "start_offset": 0,
            "end_offset": 10,
            "raw_content": "b",
        },
    )
    assert bad_offset.status_code == 409

    inverted = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session["id"],
            "sequence_number": 2,
            "start_offset": 10,
            "end_offset": 5,
            "raw_content": "b",
        },
    )
    assert inverted.status_code == 400


@pytest.mark.asyncio
async def test_disconnect_closes_session(
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
    closed = await client.post(
        "/external-ai-sessions/disconnect",
        headers=workspace.headers,
        json={"session_id": session["id"]},
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "closed"
    assert body["ended_at"] is not None

    upload = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session["id"],
            "sequence_number": 1,
            "start_offset": 0,
            "end_offset": 5,
            "raw_content": "nope",
        },
    )
    assert upload.status_code == 400

    # Reconnect after close creates a new session
    resumed = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    assert resumed["id"] != session["id"]
    assert resumed["status"] == "active"


@pytest.mark.asyncio
async def test_list_sessions_for_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    repository, branch, conversation = await _setup_repo(client, workspace)
    await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        provider="claude_code",
        machine_identifier="machine-a",
    )
    await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        provider="codex",
        machine_identifier="machine-b",
    )
    listed = await client.get(
        f"/repositories/{repository['id']}/external-ai-sessions",
        headers=workspace.headers,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_repository_isolation(
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
    )
    await _connect(
        client,
        workspace,
        repository_id=repo_b["id"],
        repository_branch_id=branch_b["id"],
        conversation_id=conversation["id"],
    )

    listed_a = await client.get(
        f"/repositories/{repo_a['id']}/external-ai-sessions",
        headers=workspace.headers,
    )
    assert listed_a.status_code == 200
    ids_a = {s["id"] for s in listed_a.json()}
    assert ids_a == {session_a["id"]}


@pytest.mark.asyncio
async def test_multiple_developers(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    member = WorkspaceContext(
        workspace_id=workspace.workspace_id,
        headers={**second_user.headers, "X-Workspace-ID": workspace.workspace_id},
        auth=second_user,
    )
    repository, branch, conversation = await _setup_repo(client, workspace)

    owner_session = await _connect(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        machine_identifier="owner-machine",
    )
    member_session = await _connect(
        client,
        member,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
        machine_identifier="member-machine",
    )
    assert owner_session["id"] != member_session["id"]
    assert owner_session["workspace_user_id"] == workspace.auth.user_id
    assert member_session["workspace_user_id"] == second_user.user_id

    listed = await client.get(
        f"/repositories/{repository['id']}/external-ai-sessions",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_permissions_cross_workspace(
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

    outsider = await register_user(client, name="Outsider")
    other_ws = await create_workspace(client, outsider)

    forbidden_list = await client.get(
        f"/repositories/{repository['id']}/external-ai-sessions",
        headers=other_ws.headers,
    )
    assert forbidden_list.status_code == 404

    forbidden_get = await client.get(
        f"/external-ai-sessions/{session['id']}",
        headers=other_ws.headers,
    )
    assert forbidden_get.status_code == 404

    forbidden_chunks = await client.get(
        f"/external-ai-sessions/{session['id']}/chunks",
        headers=other_ws.headers,
    )
    assert forbidden_chunks.status_code == 404

    forbidden_upload = await client.post(
        "/external-ai-sessions/upload",
        headers=other_ws.headers,
        json={
            "session_id": session["id"],
            "sequence_number": 1,
            "start_offset": 0,
            "end_offset": 5,
            "raw_content": "x",
        },
    )
    assert forbidden_upload.status_code == 404

    missing = await client.get(
        f"/external-ai-sessions/{uuid4()}",
        headers=workspace.headers,
    )
    assert missing.status_code == 404
