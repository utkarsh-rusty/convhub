"""Tests for Sprint 34 — Claude Handoff Adapter."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.adapters.claude.renderer import CLAUDE_HANDOFF_INSTRUCTIONS, render_claude_handoff
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


async def _enable_and_attach(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
    repository_id: str,
) -> None:
    enable = await client.post(
        f"/conversations/{conversation_id}/enable-coding",
        headers=workspace.headers,
        json={},
    )
    assert enable.status_code == 200, enable.text
    attach = await client.post(
        f"/conversations/{conversation_id}/attach-repository",
        headers=workspace.headers,
        json={"repository_id": repository_id},
    )
    assert attach.status_code == 200, attach.text


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


async def _create_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    conversation_id: str,
    title: str,
) -> dict:
    message = await _post_message(client, workspace, conversation_id, f"Work for {title}")
    response = await client.post(
        f"/conversations/{conversation_id}/commit",
        headers=workspace.headers,
        json={
            "latest_message_id": message["id"],
            "title": title,
            "description": f"Description for {title}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _get_claude_handoff(
    client: AsyncClient,
    workspace: WorkspaceContext,
    branch_id: str,
) -> str:
    response = await client.get(
        f"/repository-branches/{branch_id}/handoff/claude",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    assert "text/markdown" in response.headers.get("content-type", "")
    return response.text


def _sample_pull_package() -> dict:
    return {
        "workspace": {"id": "w1", "name": "Acme", "slug": "acme"},
        "project": {"id": "p1", "name": "Backend"},
        "repository": {
            "id": "r1",
            "name": "ConvHub API",
            "provider": "github",
            "owner": "convhub",
            "repository_name": "convhub-api",
            "remote_url": "https://github.com/convhub/convhub-api",
        },
        "repository_branch": {
            "id": "b1",
            "name": "main",
            "is_default": True,
            "is_active": True,
        },
        "repository_memory": {
            "memory_version": 2,
            "generated_at": "2026-07-11T10:00:00+00:00",
            "latest_commit_hash": "abc123",
            "latest_context_package_version": 1,
            "markdown_content": "# Repository\n\n- name: ConvHub API\n",
        },
        "transcript_snapshot": {
            "snapshot_version": 3,
            "character_count": 11,
            "updated_at": "2026-07-11T11:00:00+00:00",
            "content": "hello world",
        },
        "latest_context_package": {
            "id": "cp1",
            "version": 1,
            "commit_hash": "abc123",
            "generated_at": "2026-07-11T10:30:00+00:00",
        },
        "latest_commit": {
            "id": "c1",
            "commit_hash": "abc123",
            "title": "Ship handoff",
            "created_at": "2026-07-11T10:15:00+00:00",
        },
        "sync": {
            "sync_version": 4,
            "sync_state": "synced",
            "last_synchronized_at": "2026-07-11T10:20:00+00:00",
        },
        "active_developer": {
            "user_name": "Ada",
            "status": "active",
            "client_name": "vscode",
            "client_version": "1.0.0",
            "last_heartbeat_at": "2026-07-11T11:05:00+00:00",
        },
    }


def test_render_claude_handoff_sections_and_instructions() -> None:
    markdown = render_claude_handoff(_sample_pull_package())
    assert markdown.startswith("# ConvHub Project Handoff\n")
    for section in (
        "## Repository",
        "## Workspace",
        "## Project",
        "## Repository Branch",
        "## Current Repository Memory",
        "## Latest Context Package",
        "## Current Commit",
        "## Transcript Snapshot",
        "## Active Developer",
        "## Current Sync Status",
        "## Instructions",
    ):
        assert section in markdown
    assert CLAUDE_HANDOFF_INSTRUCTIONS in markdown
    assert "hello world" in markdown
    assert "# Repository\n\n- name: ConvHub API" in markdown
    assert "Ship handoff" in markdown
    assert "v1" in markdown


def test_render_claude_handoff_empty_package() -> None:
    markdown = render_claude_handoff(
        {
            "workspace": {},
            "project": {},
            "repository": {},
            "repository_branch": {},
            "repository_memory": None,
            "transcript_snapshot": None,
            "latest_context_package": None,
            "latest_commit": None,
            "sync": {},
            "active_developer": None,
        }
    )
    assert "# ConvHub Project Handoff" in markdown
    assert "Not Available Yet" in markdown
    assert "active developer: None" in markdown.lower() or "- active developer: None" in markdown
    assert CLAUDE_HANDOFF_INSTRUCTIONS in markdown


def test_render_claude_handoff_is_deterministic() -> None:
    payload = _sample_pull_package()
    assert render_claude_handoff(payload) == render_claude_handoff(payload)


@pytest.mark.asyncio
async def test_claude_handoff_empty_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )
    markdown = await _get_claude_handoff(client, workspace, branch["id"])
    assert "# ConvHub Project Handoff" in markdown
    assert "## Current Repository Memory" in markdown
    assert "## Transcript Snapshot" in markdown
    assert CLAUDE_HANDOFF_INSTRUCTIONS in markdown
    assert "Not Available Yet" in markdown


@pytest.mark.asyncio
async def test_claude_handoff_includes_memory_commit_package_transcript(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )
    commit = await _create_commit(
        client,
        workspace,
        conversation_id=conversation["id"],
        title="Claude handoff commit",
    )

    session = await client.post(
        "/external-ai-sessions/connect",
        headers=workspace.headers,
        json={
            "provider": "claude_code",
            "repository_id": repository["id"],
            "repository_branch_id": branch["id"],
            "conversation_id": conversation["id"],
            "machine_identifier": "claude-handoff-machine",
        },
    )
    assert session.status_code == 201, session.text
    upload = await client.post(
        "/external-ai-sessions/upload",
        headers=workspace.headers,
        json={
            "session_id": session.json()["id"],
            "sequence_number": 1,
            "start_offset": 0,
            "end_offset": 14,
            "raw_content": "handoff chunk",
        },
    )
    assert upload.status_code == 201, upload.text

    first = await _get_claude_handoff(client, workspace, branch["id"])
    second = await _get_claude_handoff(client, workspace, branch["id"])
    assert first == second
    assert "Claude handoff commit" in first
    assert commit["commit_hash"] in first
    assert "handoff chunk" in first
    assert "## Current Repository Memory" in first
    assert "## Latest Context Package" in first
    assert "## Instructions" in first


@pytest.mark.asyncio
async def test_claude_handoff_permissions(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    outsider = await register_user(client, name="Outsider")
    other_ws = await create_workspace(client, outsider)

    forbidden = await client.get(
        f"/repository-branches/{branch['id']}/handoff/claude",
        headers=other_ws.headers,
    )
    assert forbidden.status_code == 404

    missing = await client.get(
        f"/repository-branches/{uuid4()}/handoff/claude",
        headers=workspace.headers,
    )
    assert missing.status_code == 404
