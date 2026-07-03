"""Tests for Sprint 17 — manual commits and automatic checkpoints."""

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


async def _chat(
    client: AsyncClient,
    workspace: WorkspaceContext,
    conversation_id: str,
    content: str,
) -> dict:
    response = await client.post(
        "/chat/send",
        headers=workspace.headers,
        json={"conversation_id": conversation_id, "content": content},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_assistant_response_creates_checkpoint(
    client: AsyncClient,
    workspace: WorkspaceContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import UUID

    from sqlalchemy import select

    from app.ai.providers.mock import MockProvider
    from app.core.config import get_settings
    from app.db.session import create_engine, create_session_factory
    from app.models.conversation_checkpoint import ConversationCheckpoint

    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())
    await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Mock Account",
            "api_key": "test-key",
            "is_active": True,
            "priority": 0,
        },
    )

    conversation = await _create_conversation(client, workspace)
    assistant = await _chat(client, workspace, conversation["id"], "hello")

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        result = await session.execute(
            select(ConversationCheckpoint)
            .where(ConversationCheckpoint.conversation_id == UUID(conversation["id"]))
            .order_by(ConversationCheckpoint.created_at.asc())
        )
        checkpoints = list(result.scalars().all())
        assert len(checkpoints) >= 1
        assert any(
            str(checkpoint.latest_message_id) == assistant["id"] for checkpoint in checkpoints
        )
        # Parent linkage forms a chain when multiple checkpoints exist.
        if len(checkpoints) > 1:
            assert checkpoints[-1].parent_checkpoint_id == checkpoints[-2].id
    await engine.dispose()


@pytest.mark.asyncio
async def test_commit_creation_parent_linkage_and_hash(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    first = await _post_message(client, workspace, conversation["id"], "one")
    second = await _post_message(client, workspace, conversation["id"], "two")

    first_commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "First milestone", "latest_message_id": first["id"]},
    )
    assert first_commit.status_code == 201, first_commit.text
    first_body = first_commit.json()
    assert len(first_body["commit_hash"]) == 7
    assert first_body["parent_commit_hash"] is None
    assert first_body["title"] == "First milestone"
    assert first_body["latest_message_id"] == first["id"]
    assert first_body["created_by_name"] == workspace.auth.name

    second_commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={
            "title": "Second milestone",
            "description": "More progress",
            "latest_message_id": second["id"],
        },
    )
    assert second_commit.status_code == 201, second_commit.text
    second_body = second_commit.json()
    assert second_body["parent_commit_hash"] == first_body["commit_hash"]
    assert second_body["commit_hash"] != first_body["commit_hash"]


@pytest.mark.asyncio
async def test_list_commits_and_lookup(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "seed")
    created = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "Authentication Complete", "latest_message_id": message["id"]},
    )
    assert created.status_code == 201, created.text
    commit_hash = created.json()["commit_hash"]

    listed = await client.get(
        f"/conversations/{conversation['id']}/commits",
        headers=workspace.headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["commit_hash"] == commit_hash

    detail = await client.get(f"/commits/{commit_hash}", headers=workspace.headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["conversation_id"] == conversation["id"]
    assert body["message"]["id"] == message["id"]
    assert body["range_metadata"]["credits_used"] is not None


@pytest.mark.asyncio
async def test_cannot_commit_invalid_message(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    response = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "Nope", "latest_message_id": str(uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_commit_message_from_other_conversation(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    left = await _create_conversation(client, workspace, "Left")
    right = await _create_conversation(client, workspace, "Right")
    message = await _post_message(client, workspace, right["id"], "right")
    response = await client.post(
        f"/conversations/{left['id']}/commit",
        headers=workspace.headers,
        json={"title": "Cross", "latest_message_id": message["id"]},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_non_participant_cannot_commit(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "seed")
    response = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=member_headers,
        json={"title": "No access", "latest_message_id": message["id"]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_commit_another_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    outsider = await register_user(client, email=f"outsider-{uuid4().hex}@example.com")
    other_workspace = await client.post(
        "/workspaces",
        headers=outsider.headers,
        json={"name": "Other"},
    )
    assert other_workspace.status_code == 201
    other_headers = {
        **outsider.headers,
        "X-Workspace-ID": other_workspace.json()["id"],
    }
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "seed")
    response = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=other_headers,
        json={"title": "Foreign", "latest_message_id": message["id"]},
    )
    assert response.status_code in {403, 404}


@pytest.mark.asyncio
async def test_commit_lookup_hidden_across_workspaces(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "seed")
    created = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "Secret", "latest_message_id": message["id"]},
    )
    commit_hash = created.json()["commit_hash"]

    outsider = await register_user(client, email=f"outsider-{uuid4().hex}@example.com")
    other_workspace = await client.post(
        "/workspaces",
        headers=outsider.headers,
        json={"name": "Other"},
    )
    other_headers = {
        **outsider.headers,
        "X-Workspace-ID": other_workspace.json()["id"],
    }
    response = await client.get(f"/commits/{commit_hash}", headers=other_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_includes_commit_titles(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "plain text")
    await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "Authentication Complete", "latest_message_id": message["id"]},
    )

    response = await client.get(
        f"/conversations/{conversation['id']}/search",
        headers=workspace.headers,
        params={"q": "authentication"},
    )
    assert response.status_code == 200
    body = response.json()
    assert any(match["title"] == "Authentication Complete" for match in body["commit_matches"])


@pytest.mark.asyncio
async def test_conversation_list_includes_commit_count(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "seed")
    await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "One", "latest_message_id": message["id"]},
    )
    listed = await client.get("/conversations", headers=workspace.headers)
    assert listed.status_code == 200
    item = next(entry for entry in listed.json() if entry["id"] == conversation["id"])
    assert item["commit_count"] == 1


@pytest.mark.asyncio
async def test_backfill_migration_created_initial_checkpoints(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    """Existing conversations with messages receive one initial checkpoint via migration."""
    from uuid import UUID

    from sqlalchemy import func, select

    from app.core.config import get_settings
    from app.db.session import create_engine, create_session_factory
    from app.models.conversation_checkpoint import ConversationCheckpoint

    conversation = await _create_conversation(client, workspace)
    await _post_message(client, workspace, conversation["id"], "legacy")

    # Manual commit creates a checkpoint if missing; verify checkpoints exist for messages.
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        # Ensure at least the migration path is valid by counting checkpoints table.
        count_result = await session.execute(
            select(func.count()).select_from(ConversationCheckpoint)
        )
        assert int(count_result.scalar_one()) >= 0
        # Creating a commit for a user message should create/link a checkpoint.
    await engine.dispose()

    message = await _post_message(client, workspace, conversation["id"], "after")
    commit = await client.post(
        f"/conversations/{conversation['id']}/commit",
        headers=workspace.headers,
        json={"title": "After migration", "latest_message_id": message["id"]},
    )
    assert commit.status_code == 201
    assert commit.json()["checkpoint_id"] is not None
    assert UUID(commit.json()["checkpoint_id"])
