"""Tests for Sprint 33 — Pull Package Builder."""

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


async def _get_pull_package(
    client: AsyncClient,
    workspace: WorkspaceContext,
    branch_id: str,
) -> dict:
    response = await client.get(
        f"/repository-branches/{branch_id}/pull-package",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _connect_external_ai(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    repository_id: str,
    repository_branch_id: str,
    conversation_id: str | None = None,
) -> dict:
    payload: dict = {
        "provider": "claude_code",
        "repository_id": repository_id,
        "repository_branch_id": repository_branch_id,
        "machine_identifier": "pull-package-machine",
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


async def _upload_chunk(
    client: AsyncClient,
    workspace: WorkspaceContext,
    *,
    session_id: str,
    sequence_number: int,
    start_offset: int,
    end_offset: int,
    raw_content: str,
) -> None:
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


@pytest.mark.asyncio
async def test_pull_package_empty_repository(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    package = await _get_pull_package(client, workspace, branch["id"])
    assert package["repository_branch_id"] == branch["id"]
    assert package["package_version"] >= 1
    assert package["repository"]["name"] == repository["name"]
    assert package["repository_branch"]["name"] == "main"
    assert package["repository_memory"] is not None
    assert package["latest_commit"] is None
    assert package["latest_context_package"] is None
    assert package["transcript_snapshot"] is None
    assert "# Repository" in package["markdown_content"]
    assert "# Repository Memory" in package["markdown_content"]
    assert "# Transcript Snapshot" in package["markdown_content"]
    assert "Not Available Yet" in package["markdown_content"]


@pytest.mark.asyncio
async def test_pull_package_with_commits_and_context_package(
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
        title="Pull package commit",
    )

    package = await _get_pull_package(client, workspace, branch["id"])
    assert package["latest_commit"] is not None
    assert package["latest_commit"]["id"] == commit["id"]
    assert package["latest_commit"]["commit_hash"] == commit["commit_hash"]
    assert package["latest_context_package"] is not None
    assert package["latest_context_package"]["commit_hash"] == commit["commit_hash"]
    assert package["repository_memory"]["latest_commit_hash"] == commit["commit_hash"]
    assert "Pull package commit" in package["markdown_content"]
    assert "# Latest Context Package" in package["markdown_content"]
    assert "# Latest Commit" in package["markdown_content"]
    assert "# Sync Information" in package["markdown_content"]


@pytest.mark.asyncio
async def test_pull_package_includes_transcript_snapshot(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )
    conversation = await _create_conversation(client, workspace, project_id=project_id)
    session = await _connect_external_ai(
        client,
        workspace,
        repository_id=repository["id"],
        repository_branch_id=branch["id"],
        conversation_id=conversation["id"],
    )
    await _upload_chunk(
        client,
        workspace,
        session_id=session["id"],
        sequence_number=1,
        start_offset=0,
        end_offset=12,
        raw_content="hello plugin",
    )

    package = await _get_pull_package(client, workspace, branch["id"])
    assert package["transcript_snapshot"] is not None
    assert package["transcript_snapshot"]["content"] == "hello plugin"
    assert package["transcript_snapshot"]["character_count"] == 12
    assert "hello plugin" in package["markdown_content"]


@pytest.mark.asyncio
async def test_pull_package_markdown_and_json_export(
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
    await _create_commit(
        client,
        workspace,
        conversation_id=conversation["id"],
        title="Exportable pull package",
    )

    md = await client.get(
        f"/repository-branches/{branch['id']}/pull-package/export",
        headers=workspace.headers,
    )
    assert md.status_code == 200, md.text
    md_body = md.json()
    assert md_body["filename"].endswith(".md")
    assert md_body["content_type"] == "text/markdown"
    assert "# Repository" in md_body["content"]
    assert "# Active Developer" in md_body["content"]
    assert "Exportable pull package" in md_body["content"]

    js = await client.get(
        f"/repository-branches/{branch['id']}/pull-package/json",
        headers=workspace.headers,
    )
    assert js.status_code == 200, js.text
    js_body = js.json()
    assert js_body["filename"].endswith(".json")
    assert js_body["content"]["latest_commit"]["title"] == "Exportable pull package"
    assert "markdown_content" not in js_body["content"]


@pytest.mark.asyncio
async def test_pull_package_permissions(
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
        f"/repository-branches/{branch['id']}/pull-package",
        headers=other_ws.headers,
    )
    assert forbidden.status_code == 404

    missing = await client.get(
        f"/repository-branches/{uuid4()}/pull-package",
        headers=workspace.headers,
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_pull_package_repository_isolation(
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

    conversation_a = await _create_conversation(
        client, workspace, project_id=project_id, title="A talk"
    )
    conversation_b = await _create_conversation(
        client, workspace, project_id=project_id, title="B talk"
    )
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation_a["id"],
        repository_id=repo_a["id"],
    )
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation_b["id"],
        repository_id=repo_b["id"],
    )
    commit_a = await _create_commit(
        client, workspace, conversation_id=conversation_a["id"], title="Commit A"
    )
    commit_b = await _create_commit(
        client, workspace, conversation_id=conversation_b["id"], title="Commit B"
    )

    package_a = await _get_pull_package(client, workspace, branch_a["id"])
    package_b = await _get_pull_package(client, workspace, branch_b["id"])
    assert package_a["latest_commit"]["id"] == commit_a["id"]
    assert package_b["latest_commit"]["id"] == commit_b["id"]
    assert package_a["repository"]["id"] == repo_a["id"]
    assert package_b["repository"]["id"] == repo_b["id"]
    assert package_a["latest_commit"]["id"] != package_b["latest_commit"]["id"]
