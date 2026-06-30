from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import get_settings
from app.core.jwt import TokenError, decode_access_token
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.realtime.events import RealtimeEvent, RealtimeEventType
from app.realtime.manager import get_ws_manager
from app.realtime.schemas import ClientPing, ClientSubscribe, ClientTyping

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["realtime"])


async def _authenticate(token: str) -> User | None:
    settings = get_settings()
    try:
        payload = decode_access_token(token, settings)
        user_id = UUID(str(payload["sub"]))
    except (TokenError, ValueError):
        return None

    from app.main import app

    session_factory = app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def _verify_workspace_member(workspace_id: UUID, user_id: UUID) -> bool:
    from app.main import app

    session_factory = app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None


@router.websocket("/ws")
async def realtime_websocket(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4401)
        return

    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=4401)
        return

    manager = get_ws_manager()
    connection_id = uuid4()
    connection = await manager.connect(
        websocket,
        connection_id=connection_id,
        user_id=user.id,
        user_name=user.name,
    )

    await manager.send_to_connection(
        connection_id,
        RealtimeEvent(
            type=RealtimeEventType.CONNECTED,
            workspace_id=user.id,
            payload={"user_id": str(user.id), "user_name": user.name},
        ),
    )

    heartbeat_task = None
    try:
        import asyncio

        heartbeat_task = asyncio.create_task(manager.run_heartbeat(connection_id))

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = data.get("action")
            if action == "ping":
                ClientPing.model_validate(data)
                await manager.send_to_connection(
                    connection_id,
                    RealtimeEvent(
                        type=RealtimeEventType.PONG,
                        workspace_id=connection.workspace_id or user.id,
                        payload={},
                    ),
                )
                continue

            if action == "subscribe":
                message = ClientSubscribe.model_validate(data)
                if not await _verify_workspace_member(message.workspace_id, user.id):
                    await manager.send_to_connection(
                        connection_id,
                        RealtimeEvent(
                            type=RealtimeEventType.ERROR,
                            workspace_id=message.workspace_id,
                            payload={"detail": "Not a workspace member"},
                        ),
                    )
                    continue
                await manager.subscribe_workspace(connection_id, message.workspace_id)
                if message.conversation_ids:
                    await manager.subscribe_conversations(connection_id, message.conversation_ids)
                continue

            if action in {"typing.started", "typing.stopped"}:
                typing = ClientTyping.model_validate(data)
                await manager.handle_typing(
                    connection_id,
                    typing.conversation_id,
                    started=action == "typing.started",
                )
                continue

    except WebSocketDisconnect:
        pass
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
        await manager.disconnect(connection_id)
