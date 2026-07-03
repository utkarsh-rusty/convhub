"""Realtime collaboration websocket tests."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.main import app

WS_PATH = "/api/v1/realtime/ws"


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def _register_user(
    client: TestClient,
    *,
    name: str | None = None,
    email: str | None = None,
    password: str = "password123",
) -> tuple[str, str, str, dict[str, str]]:
    email = email or f"user-{uuid4().hex}@example.com"
    name = name or "Test User"
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return token, user_id, email, headers


def _create_workspace(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str | None = None,
) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={"name": name or f"Workspace {uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    workspace_id = response.json()["id"]
    workspace_headers = {**headers, "X-Workspace-ID": workspace_id}
    return workspace_id, workspace_headers


def _invite_and_accept(
    client: TestClient,
    workspace_headers: dict[str, str],
    invitee_headers: dict[str, str],
    invitee_email: str,
) -> None:
    invite = client.post(
        f"/api/v1/workspaces/{workspace_headers['X-Workspace-ID']}/invite",
        headers=workspace_headers,
        json={"email": invitee_email, "role": "member"},
    )
    assert invite.status_code == 201, invite.text
    accept = client.post(
        f"/api/v1/invitations/{invite.json()['token']}/accept",
        headers=invitee_headers,
    )
    assert accept.status_code == 200, accept.text


def _connect_ws(client: TestClient, token: str):
    return client.websocket_connect(f"{WS_PATH}?token={token}")


def _subscribe_ws(
    websocket,
    *,
    workspace_id: str,
    conversation_ids: list[str] | None = None,
) -> None:
    websocket.send_json(
        {
            "action": "subscribe",
            "workspace_id": workspace_id,
            "conversation_ids": conversation_ids or [],
        }
    )


def _receive_event(websocket, *, allowed: set[str] | None = None, max_attempts: int = 20) -> dict:
    for _ in range(max_attempts):
        event = websocket.receive_json()
        if allowed is None or event["type"] in allowed:
            return event
    raise AssertionError(f"No matching event in {max_attempts} attempts")


def test_websocket_connect_and_subscribe(api_client: TestClient) -> None:
    token, _, _, headers = _register_user(api_client)
    workspace_id, _ = _create_workspace(api_client, headers)

    with _connect_ws(api_client, token) as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "connected"

        _subscribe_ws(websocket, workspace_id=workspace_id)
        websocket.send_json({"action": "ping"})
        pong = _receive_event(websocket, allowed={"pong"})
        assert pong["type"] == "pong"


def test_message_created_broadcasts_to_subscribers(api_client: TestClient) -> None:
    alice_token, alice_id, _, alice_headers = _register_user(api_client, name="Alice")
    bob_token, bob_id, bob_email, bob_headers = _register_user(
        api_client,
        name="Bob",
        email=f"bob-{uuid4().hex}@example.com",
    )
    workspace_id, workspace_headers = _create_workspace(api_client, alice_headers)
    _invite_and_accept(api_client, workspace_headers, bob_headers, bob_email)

    conv = api_client.post(
        "/api/v1/conversations",
        headers=workspace_headers,
        json={"title": "Realtime"},
    )
    conversation_id = conv.json()["id"]

    api_client.post(
        f"/api/v1/conversations/{conversation_id}/participants",
        headers=workspace_headers,
        json={"user_ids": [bob_id]},
    )

    with _connect_ws(api_client, bob_token) as websocket:
        websocket.receive_json()
        _subscribe_ws(
            websocket,
            workspace_id=workspace_id,
            conversation_ids=[conversation_id],
        )

        created = api_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={**alice_headers, "X-Workspace-ID": workspace_id},
            json={"content": "Hello team", "role": "user"},
        )
        assert created.status_code == 201

        event = _receive_event(
            websocket,
            allowed={"message.created", "conversation.updated"},
        )
        if event["type"] == "conversation.updated":
            event = _receive_event(websocket, allowed={"message.created"})

        assert event["type"] == "message.created"
        assert event["payload"]["content"] == "Hello team"


def test_typing_events_broadcast(api_client: TestClient) -> None:
    alice_token, _, alice_email, alice_headers = _register_user(api_client, name="Alice")
    bob_token, _, bob_email, bob_headers = _register_user(
        api_client,
        name="Bob",
        email=f"bob-{uuid4().hex}@example.com",
    )
    workspace_id, workspace_headers = _create_workspace(api_client, alice_headers)
    _invite_and_accept(api_client, workspace_headers, bob_headers, bob_email)

    conv = api_client.post(
        "/api/v1/conversations",
        headers=workspace_headers,
        json={"title": "Typing"},
    )
    conversation_id = conv.json()["id"]

    with _connect_ws(api_client, bob_token) as bob_ws:
        bob_ws.receive_json()
        _subscribe_ws(
            bob_ws,
            workspace_id=workspace_id,
            conversation_ids=[conversation_id],
        )

        with _connect_ws(api_client, alice_token) as alice_ws:
            alice_ws.receive_json()
            _subscribe_ws(
                alice_ws,
                workspace_id=workspace_id,
                conversation_ids=[conversation_id],
            )
            alice_ws.send_json(
                {"action": "typing.started", "conversation_id": conversation_id},
            )

            event = _receive_event(bob_ws, allowed={"typing.started"})
            assert event["type"] == "typing.started"
            assert event["payload"]["user_name"] == "Alice"


def test_websocket_rejects_invalid_token(api_client: TestClient) -> None:
    with pytest.raises(Exception):
        with _connect_ws(api_client, "invalid"):
            pass


def test_websocket_disconnect_and_reconnect(api_client: TestClient) -> None:
    token, _, _, headers = _register_user(api_client)
    workspace_id, _ = _create_workspace(api_client, headers)

    with _connect_ws(api_client, token) as websocket:
        assert websocket.receive_json()["type"] == "connected"

    with _connect_ws(api_client, token) as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "connected"
        _subscribe_ws(websocket, workspace_id=workspace_id)
        websocket.send_json({"action": "ping"})
        assert _receive_event(websocket, allowed={"pong"})["type"] == "pong"


def test_multiple_clients_receive_broadcast(api_client: TestClient) -> None:
    alice_token, alice_id, _, alice_headers = _register_user(api_client, name="Alice")
    bob_token, bob_id, bob_email, bob_headers = _register_user(
        api_client,
        name="Bob",
        email=f"bob-{uuid4().hex}@example.com",
    )
    workspace_id, workspace_headers = _create_workspace(api_client, alice_headers)
    _invite_and_accept(api_client, workspace_headers, bob_headers, bob_email)

    conv = api_client.post(
        "/api/v1/conversations",
        headers=workspace_headers,
        json={"title": "Multi"},
    )
    conversation_id = conv.json()["id"]

    with (
        _connect_ws(api_client, alice_token) as alice_ws,
        _connect_ws(api_client, bob_token) as bob_ws,
    ):
        alice_ws.receive_json()
        bob_ws.receive_json()
        _subscribe_ws(
            alice_ws,
            workspace_id=workspace_id,
            conversation_ids=[conversation_id],
        )
        _subscribe_ws(
            bob_ws,
            workspace_id=workspace_id,
            conversation_ids=[conversation_id],
        )

        created = api_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={**alice_headers, "X-Workspace-ID": workspace_id},
            json={"content": "Everyone sees this", "role": "user"},
        )
        assert created.status_code == 201

        alice_event = _receive_event(
            alice_ws,
            allowed={"message.created", "conversation.updated"},
        )
        bob_event = _receive_event(
            bob_ws,
            allowed={"message.created", "conversation.updated"},
        )
        if alice_event["type"] == "conversation.updated":
            alice_event = _receive_event(alice_ws, allowed={"message.created"})
        if bob_event["type"] == "conversation.updated":
            bob_event = _receive_event(bob_ws, allowed={"message.created"})

        assert alice_event["type"] == "message.created"
        assert bob_event["type"] == "message.created"


def test_streaming_chat_emits_completed_event(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ai.providers.mock import MockProvider

    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())

    token, _, _, headers = _register_user(api_client)
    workspace_id, workspace_headers = _create_workspace(api_client, headers)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=workspace_headers,
        json={"title": "Stream"},
    )
    conversation_id = conv.json()["id"]

    with _connect_ws(api_client, token) as websocket:
        websocket.receive_json()
        _subscribe_ws(
            websocket,
            workspace_id=workspace_id,
            conversation_ids=[conversation_id],
        )

        response = api_client.post(
            "/api/v1/chat/send",
            headers=workspace_headers,
            json={"conversation_id": conversation_id, "content": "stream please"},
        )
        assert response.status_code == 200

        saw_streaming = False
        saw_completed = False
        for _ in range(30):
            event = websocket.receive_json()
            if event["type"] == "message.streaming":
                saw_streaming = True
            if event["type"] == "message.completed":
                saw_completed = True
                break

        assert saw_streaming
        assert saw_completed
