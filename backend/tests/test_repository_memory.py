"""Tests for Sprint 30 — Repository Memory Builder v1."""

from __future__ import annotations

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


async def _get_memory(
    client: AsyncClient,
    workspace: WorkspaceContext,
    branch_id: str,
) -> dict:
    response = await client.get(
        f"/repository-branches/{branch_id}/repository-memory",
        headers=workspace.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_repository_memory_generated_on_branch_creation(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-owner@example.com")
    workspace = await create_workspace(client, user, name="RM Lab")
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    memory = await _get_memory(client, workspace, branch["id"])
    assert memory["repository_branch_id"] == branch["id"]
    assert memory["memory_version"] >= 1
    assert memory["latest_commit_id"] is None
    assert memory["latest_context_package_id"] is None
    assert "Not documented." in memory["markdown_content"]
    assert "No recorded decisions." in memory["markdown_content"]
    assert "No pending TODOs." in memory["markdown_content"]
    assert memory["json_content"]["repository"]["name"] == repository["name"]
    assert memory["json_content"]["repository_branch"]["name"] == "main"


async def test_repository_memory_empty_repository(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-empty@example.com")
    workspace = await create_workspace(client, user, name="Empty RM")
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    memory = await _get_memory(client, workspace, branch["id"])
    assert memory["json_content"]["active_conversation"] is None
    assert memory["json_content"]["latest_commit"] is None
    assert memory["json_content"]["participants"] == []
    assert memory["json_content"]["recent_commits"] == []
    assert "No commits yet." in memory["markdown_content"]


async def test_repository_memory_regenerates_on_attach_and_commit(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-regen@example.com", name="Regen Owner")
    workspace = await create_workspace(client, user, name="Regen RM")
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    before = await _get_memory(client, workspace, branch["id"])
    version_before = before["memory_version"]

    conversation = await _create_conversation(client, workspace, project_id=project_id)
    await _enable_and_attach(
        client,
        workspace,
        conversation_id=conversation["id"],
        repository_id=repository["id"],
    )

    after_attach = await _get_memory(client, workspace, branch["id"])
    assert after_attach["memory_version"] > version_before
    assert after_attach["json_content"]["active_conversation"]["id"] == conversation["id"]
    assert after_attach["json_content"]["active_conversation"]["owner"] == user.name

    commit = await _create_commit(
        client,
        workspace,
        conversation_id=conversation["id"],
        title="Add repository memory builder",
    )
    after_commit = await _get_memory(client, workspace, branch["id"])
    assert after_commit["memory_version"] > after_attach["memory_version"]
    assert after_commit["latest_commit_id"] == commit["id"]
    assert after_commit["latest_commit_hash"] == commit["commit_hash"]
    assert after_commit["latest_context_package_id"] is not None
    assert "Add repository memory builder" in after_commit["markdown_content"]
    assert after_commit["json_content"]["latest_context_package"] is not None


async def test_repository_memory_multiple_commits(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-multi@example.com")
    workspace = await create_workspace(client, user, name="Multi RM")
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

    await _create_commit(client, workspace, conversation_id=conversation["id"], title="First")
    await _create_commit(client, workspace, conversation_id=conversation["id"], title="Second")
    third = await _create_commit(
        client, workspace, conversation_id=conversation["id"], title="Third"
    )

    memory = await _get_memory(client, workspace, branch["id"])
    assert memory["latest_commit_id"] == third["id"]
    recent = memory["json_content"]["recent_commits"]
    assert len(recent) == 3
    assert recent[0]["title"] == "Third"
    assert recent[2]["title"] == "First"
    packages = memory["json_content"]["context_package_references"]
    assert len(packages) == 3


async def test_repository_memory_restore_regenerates(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-restore@example.com")
    workspace = await create_workspace(client, user, name="Restore RM")
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
        client, workspace, conversation_id=conversation["id"], title="Checkpoint"
    )
    before = await _get_memory(client, workspace, branch["id"])

    package_id = before["latest_context_package_id"]
    assert package_id is not None

    restore = await client.post(
        f"/context-packages/{package_id}/restore",
        headers=workspace.headers,
        json={"conversation_name": "Restored conversation"},
    )
    assert restore.status_code == 201, restore.text

    after = await _get_memory(client, workspace, branch["id"])
    assert after["memory_version"] > before["memory_version"]
    assert after["json_content"]["active_conversation"]["title"] == "Restored conversation"
    history_types = [item["sync_type"] for item in after["json_content"]["branch_history"]]
    assert "restore" in history_types
    assert after["latest_commit_id"] == commit["id"]


async def test_repository_memory_markdown_and_json_export(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-export@example.com")
    workspace = await create_workspace(client, user, name="Export RM")
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
        client, workspace, conversation_id=conversation["id"], title="Exportable commit"
    )

    markdown = await client.get(
        f"/repository-branches/{branch['id']}/repository-memory/export",
        headers=workspace.headers,
    )
    assert markdown.status_code == 200, markdown.text
    md_payload = markdown.json()
    assert md_payload["filename"].endswith(".md")
    assert md_payload["content_type"] == "text/markdown"
    assert "# Repository" in md_payload["content"]
    assert "Exportable commit" in md_payload["content"]

    json_export = await client.get(
        f"/repository-branches/{branch['id']}/repository-memory/json",
        headers=workspace.headers,
    )
    assert json_export.status_code == 200, json_export.text
    json_payload = json_export.json()
    assert json_payload["filename"].endswith(".json")
    assert json_payload["content"]["repository"]["name"] == repository["name"]
    assert json_payload["content"]["latest_commit"]["title"] == "Exportable commit"


async def test_repository_memory_branch_creation_isolated(client: AsyncClient) -> None:
    user = await register_user(client, email="rm-branch@example.com")
    workspace = await create_workspace(client, user, name="Branch RM")
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    main = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )
    feature = await _create_branch(
        client, workspace, repository_id=repository["id"], name="feature/memory", is_default=False
    )

    main_memory = await _get_memory(client, workspace, main["id"])
    feature_memory = await _get_memory(client, workspace, feature["id"])
    assert main_memory["id"] != feature_memory["id"]
    assert main_memory["repository_branch_id"] == main["id"]
    assert feature_memory["repository_branch_id"] == feature["id"]
    assert feature_memory["json_content"]["repository_branch"]["name"] == "feature/memory"


async def test_branch_memory_endpoints_still_work(client: AsyncClient) -> None:
    """Existing Branch Memory routes must remain unchanged."""
    user = await register_user(client, email="rm-compat@example.com")
    workspace = await create_workspace(client, user, name="Compat RM")
    project_id = await _create_project(client, workspace)
    repository = await _create_repository(client, workspace, project_id=project_id)
    branch = await _create_branch(
        client, workspace, repository_id=repository["id"], name="main", is_default=True
    )

    branch_memory = await client.get(
        f"/repository-branches/{branch['id']}/memory",
        headers=workspace.headers,
    )
    assert branch_memory.status_code == 200, branch_memory.text
    assert "sync_status" in branch_memory.json()

    repo_memory = await client.get(
        f"/repository-branches/{branch['id']}/repository-memory",
        headers=workspace.headers,
    )
    assert repo_memory.status_code == 200, repo_memory.text
    assert "markdown_content" in repo_memory.json()
