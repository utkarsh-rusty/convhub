"""Tests for Sprint 15.5 — branch ownership and conversation membership."""

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


async def _member_headers(
    client: AsyncClient,
    workspace: WorkspaceContext,
    user: AuthContext,
) -> dict[str, str]:
    await invite_and_accept(client, workspace, user)
    return {
        **user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }


@pytest.mark.asyncio
async def test_branch_owner_is_branch_creator(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    message = await _post_message(client, workspace, conversation["id"], "hi")

    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=member_headers,
        json={"message_id": message["id"], "branch_name": "Bob's branch"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()
    assert branch["owner_id"] == second_user.user_id
    assert branch["owner"]["user_id"] == second_user.user_id
    assert branch["owner"]["name"] == second_user.name
    assert branch["is_participant"] is True


@pytest.mark.asyncio
async def test_branch_participants_contain_only_creator(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    message = await _post_message(client, workspace, conversation["id"], "hi")

    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=member_headers,
        json={"message_id": message["id"], "branch_name": "Solo"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()

    participants = await client.get(
        f"/conversations/{branch['id']}/participants",
        headers=member_headers,
    )
    assert participants.status_code == 200
    participant_ids = [p["user_id"] for p in participants.json()]
    assert participant_ids == [second_user.user_id]
    assert branch["participant_count"] == 1


@pytest.mark.asyncio
async def test_parent_participants_unchanged_after_branch(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )
    message = await _post_message(client, workspace, conversation["id"], "hi")

    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Side"},
    )
    assert branch_response.status_code == 201, branch_response.text

    parent_participants = await client.get(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
    )
    assert parent_participants.status_code == 200
    parent_ids = {p["user_id"] for p in parent_participants.json()}
    assert parent_ids == {workspace.auth.user_id, second_user.user_id}


@pytest.mark.asyncio
async def test_owner_can_remove_participant(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )

    removed = await client.delete(
        f"/conversations/{conversation['id']}/participants/{second_user.user_id}",
        headers=workspace.headers,
    )
    assert removed.status_code == 204

    participants = await client.get(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
    )
    assert {p["user_id"] for p in participants.json()} == {workspace.auth.user_id}


@pytest.mark.asyncio
async def test_non_owner_cannot_remove_participant(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    third = await register_user(client, email=f"third-{uuid4().hex}@example.com")
    await invite_and_accept(client, workspace, third)

    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id, third.user_id]},
    )

    response = await client.delete(
        f"/conversations/{conversation['id']}/participants/{third.user_id}",
        headers=member_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_remove_owner(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    conversation = await _create_conversation(client, workspace)
    response = await client.delete(
        f"/conversations/{conversation['id']}/participants/{workspace.auth.user_id}",
        headers=workspace.headers,
    )
    assert response.status_code == 400
    assert "owner" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_removed_participant_receives_403_on_chat(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )

    await client.delete(
        f"/conversations/{conversation['id']}/participants/{second_user.user_id}",
        headers=workspace.headers,
    )

    message_response = await client.post(
        f"/conversations/{conversation['id']}/messages",
        headers=member_headers,
        json={"content": "should fail", "role": "user"},
    )
    assert message_response.status_code == 403

    chat_response = await client.post(
        "/chat/send",
        headers=member_headers,
        json={"conversation_id": conversation["id"], "content": "should fail"},
    )
    assert chat_response.status_code == 403


@pytest.mark.asyncio
async def test_read_only_users_can_view_but_cannot_send_messages(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    message = await _post_message(client, workspace, conversation["id"], "visible")

    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Private branch"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()

    detail = await client.get(
        f"/conversations/{branch['id']}",
        headers=member_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["is_participant"] is False
    assert detail.json()["owner_id"] == workspace.auth.user_id

    messages = await client.get(
        f"/conversations/{branch['id']}/messages",
        headers=member_headers,
    )
    assert messages.status_code == 200
    assert [m["content"] for m in messages.json()] == ["visible"]

    send = await client.post(
        f"/conversations/{branch['id']}/messages",
        headers=member_headers,
        json={"content": "nope", "role": "user"},
    )
    assert send.status_code == 403

    invite = await client.post(
        f"/conversations/{branch['id']}/participants",
        headers=member_headers,
        json={"user_ids": [second_user.user_id]},
    )
    assert invite.status_code == 403

    rename = await client.patch(
        f"/conversations/{branch['id']}",
        headers=member_headers,
        json={"title": "Hijacked"},
    )
    assert rename.status_code == 403


@pytest.mark.asyncio
async def test_workspace_members_see_branch_tree_with_membership_flags(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace, "Main")
    message = await _post_message(client, workspace, conversation["id"], "hi")
    branch_response = await client.post(
        f"/conversations/{conversation['id']}/branch",
        headers=workspace.headers,
        json={"message_id": message["id"], "branch_name": "Side"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch = branch_response.json()

    listed = await client.get("/conversations", headers=member_headers)
    assert listed.status_code == 200
    items = {item["id"]: item for item in listed.json()}
    assert conversation["id"] in items
    assert branch["id"] in items
    assert items[conversation["id"]]["is_participant"] is False
    assert items[branch["id"]]["is_participant"] is False
    assert items[branch["id"]]["owner_id"] == workspace.auth.user_id


@pytest.mark.asyncio
async def test_routing_and_borrow_ignore_removed_participant(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    """Removed participants are excluded from participant-scoped routing/borrow."""
    from uuid import UUID

    from sqlalchemy import select

    from app.core.config import get_settings
    from app.db.session import create_engine, create_session_factory
    from app.models.conversation_participant import ConversationParticipant

    member_headers = await _member_headers(client, workspace, second_user)
    conversation = await _create_conversation(client, workspace)
    await client.post(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
        json={"user_ids": [second_user.user_id]},
    )

    await client.delete(
        f"/conversations/{conversation['id']}/participants/{second_user.user_id}",
        headers=workspace.headers,
    )

    participants = await client.get(
        f"/conversations/{conversation['id']}/participants",
        headers=workspace.headers,
    )
    participant_ids = {p["user_id"] for p in participants.json()}
    assert second_user.user_id not in participant_ids
    assert workspace.auth.user_id in participant_ids

    # Gateway and borrow engine load eligible users from ConversationParticipant rows.
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        result = await session.execute(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == UUID(conversation["id"])
            )
        )
        loaded_ids = {str(user_id) for user_id in result.scalars().all()}
        assert second_user.user_id not in loaded_ids
        assert workspace.auth.user_id in loaded_ids
        eligible_for_borrow = frozenset(
            user_id for user_id in loaded_ids if user_id != workspace.auth.user_id
        )
        assert second_user.user_id not in eligible_for_borrow
    await engine.dispose()

    chat_response = await client.post(
        "/chat/send",
        headers=member_headers,
        json={"conversation_id": conversation["id"], "content": "borrow?"},
    )
    assert chat_response.status_code == 403
