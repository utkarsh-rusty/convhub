from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.realtime.events import RealtimeEvent, RealtimeEventType

logger = logging.getLogger(__name__)

TYPING_TIMEOUT = timedelta(seconds=5)
HEARTBEAT_INTERVAL_SECONDS = 30


@dataclass
class ClientConnection:
    websocket: WebSocket
    user_id: UUID
    user_name: str
    workspace_id: UUID | None = None
    conversation_ids: set[UUID] = field(default_factory=set)


@dataclass
class PresenceState:
    user_id: UUID
    user_name: str
    status: str
    last_seen: datetime


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, ClientConnection] = {}
        self._workspace_connections: dict[UUID, set[UUID]] = {}
        self._conversation_connections: dict[UUID, set[UUID]] = {}
        self._user_connections: dict[UUID, set[UUID]] = {}
        self._presence: dict[UUID, dict[UUID, PresenceState]] = {}
        self._typing: dict[UUID, dict[UUID, datetime]] = {}
        self._lock = asyncio.Lock()
        self._typing_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._typing_task is None:
            self._typing_task = asyncio.create_task(self._typing_expiry_loop())

    async def stop(self) -> None:
        if self._typing_task is not None:
            self._typing_task.cancel()
            try:
                await self._typing_task
            except asyncio.CancelledError:
                pass
            self._typing_task = None

    async def connect(
        self,
        websocket: WebSocket,
        *,
        connection_id: UUID,
        user_id: UUID,
        user_name: str,
    ) -> ClientConnection:
        await websocket.accept()
        connection = ClientConnection(
            websocket=websocket,
            user_id=user_id,
            user_name=user_name,
        )
        async with self._lock:
            self._connections[connection_id] = connection
            self._user_connections.setdefault(user_id, set()).add(connection_id)
        return connection

    async def disconnect(self, connection_id: UUID) -> None:
        workspace_id: UUID | None = None
        disconnected_user_id: UUID | None = None
        disconnected_user_name: str | None = None
        should_emit_member_left = False

        async with self._lock:
            connection = self._connections.pop(connection_id, None)
            if connection is None:
                return

            if connection.user_id in self._user_connections:
                self._user_connections[connection.user_id].discard(connection_id)
                if not self._user_connections[connection.user_id]:
                    del self._user_connections[connection.user_id]

            if connection.workspace_id is not None:
                workspace_id = connection.workspace_id
                self._workspace_connections.get(workspace_id, set()).discard(connection_id)
                self._update_presence_locked(
                    workspace_id,
                    connection.user_id,
                    connection.user_name,
                    "offline",
                )
                remaining = self._workspace_connections.get(workspace_id, set())
                user_still_online = any(
                    self._connections.get(conn_id) is not None
                    and self._connections[conn_id].user_id == connection.user_id
                    for conn_id in remaining
                )
                if not user_still_online:
                    should_emit_member_left = True
                    disconnected_user_id = connection.user_id
                    disconnected_user_name = connection.user_name

            for conversation_id in connection.conversation_ids:
                self._conversation_connections.get(conversation_id, set()).discard(connection_id)

        if workspace_id is not None:
            await self._broadcast_presence_unlocked(workspace_id)
            if should_emit_member_left and disconnected_user_id is not None:
                await self.broadcast_workspace(
                    workspace_id,
                    RealtimeEvent(
                        type=RealtimeEventType.MEMBER_LEFT,
                        workspace_id=workspace_id,
                        payload={
                            "user_id": str(disconnected_user_id),
                            "user_name": disconnected_user_name or "",
                            "status": "offline",
                        },
                    ),
                )

    async def subscribe_workspace(
        self,
        connection_id: UUID,
        workspace_id: UUID,
    ) -> None:
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return

            if connection.workspace_id is not None and connection.workspace_id != workspace_id:
                old_workspace = connection.workspace_id
                self._workspace_connections.get(old_workspace, set()).discard(connection_id)
                self._update_presence_locked(old_workspace, connection.user_id, connection.user_name, "offline")

            connection.workspace_id = workspace_id
            self._workspace_connections.setdefault(workspace_id, set()).add(connection_id)
            self._update_presence_locked(workspace_id, connection.user_id, connection.user_name, "online")

        await self._broadcast_presence_unlocked(workspace_id)
        await self.broadcast_workspace(
            workspace_id,
            RealtimeEvent(
                type=RealtimeEventType.MEMBER_JOINED,
                workspace_id=workspace_id,
                payload={
                    "user_id": str(connection.user_id),
                    "user_name": connection.user_name,
                    "status": "online",
                },
            ),
            exclude_connection_id=connection_id,
        )

    async def subscribe_conversations(
        self,
        connection_id: UUID,
        conversation_ids: list[UUID],
    ) -> None:
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return
            for conversation_id in conversation_ids:
                connection.conversation_ids.add(conversation_id)
                self._conversation_connections.setdefault(conversation_id, set()).add(connection_id)

    async def handle_typing(
        self,
        connection_id: UUID,
        conversation_id: UUID,
        *,
        started: bool,
    ) -> None:
        connection = self._connections.get(connection_id)
        if connection is None or connection.workspace_id is None:
            return

        workspace_id = connection.workspace_id
        now = datetime.now(UTC)

        if started:
            self._typing.setdefault(conversation_id, {})[connection.user_id] = now + TYPING_TIMEOUT
            event_type = RealtimeEventType.TYPING_STARTED
        else:
            self._typing.get(conversation_id, {}).pop(connection.user_id, None)
            event_type = RealtimeEventType.TYPING_STOPPED

        await self.broadcast_conversation(
            workspace_id,
            conversation_id,
            RealtimeEvent(
                type=event_type,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                payload={
                    "user_id": str(connection.user_id),
                    "user_name": connection.user_name,
                },
            ),
            exclude_connection_id=connection_id,
        )

    async def send_to_connection(self, connection_id: UUID, event: RealtimeEvent) -> None:
        connection = self._connections.get(connection_id)
        if connection is None:
            return
        try:
            await connection.websocket.send_json(event.to_wire())
        except (WebSocketDisconnect, RuntimeError):
            await self.disconnect(connection_id)

    async def broadcast_workspace(
        self,
        workspace_id: UUID,
        event: RealtimeEvent,
        *,
        exclude_connection_id: UUID | None = None,
    ) -> None:
        connection_ids = list(self._workspace_connections.get(workspace_id, set()))
        await self._broadcast_to_connections(connection_ids, event, exclude_connection_id)

    async def broadcast_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        event: RealtimeEvent,
        *,
        exclude_connection_id: UUID | None = None,
    ) -> None:
        event.workspace_id = workspace_id
        event.conversation_id = conversation_id
        connection_ids = list(self._conversation_connections.get(conversation_id, set()))
        await self._broadcast_to_connections(connection_ids, event, exclude_connection_id)

    async def broadcast_user(
        self,
        user_id: UUID,
        event: RealtimeEvent,
    ) -> None:
        connection_ids = list(self._user_connections.get(user_id, set()))
        await self._broadcast_to_connections(connection_ids, event, None)

    async def _broadcast_to_connections(
        self,
        connection_ids: list[UUID],
        event: RealtimeEvent,
        exclude_connection_id: UUID | None,
    ) -> None:
        wire = event.to_wire()
        stale: list[UUID] = []
        for connection_id in connection_ids:
            if connection_id == exclude_connection_id:
                continue
            connection = self._connections.get(connection_id)
            if connection is None:
                stale.append(connection_id)
                continue
            try:
                await connection.websocket.send_json(wire)
            except (WebSocketDisconnect, RuntimeError):
                stale.append(connection_id)
        for connection_id in stale:
            await self.disconnect(connection_id)

    def _update_presence_locked(
        self,
        workspace_id: UUID,
        user_id: UUID,
        user_name: str,
        status: str,
    ) -> None:
        now = datetime.now(UTC)
        self._presence.setdefault(workspace_id, {})[user_id] = PresenceState(
            user_id=user_id,
            user_name=user_name,
            status=status,
            last_seen=now,
        )

    async def _broadcast_presence_unlocked(self, workspace_id: UUID) -> None:
        members = self._presence.get(workspace_id, {})
        for presence in members.values():
            await self.broadcast_workspace(
                workspace_id,
                RealtimeEvent(
                    type=RealtimeEventType.PRESENCE_UPDATED,
                    workspace_id=workspace_id,
                    payload={
                        "user_id": str(presence.user_id),
                        "user_name": presence.user_name,
                        "status": presence.status,
                        "last_seen": presence.last_seen.isoformat(),
                    },
                ),
            )

    async def _typing_expiry_loop(self) -> None:
        while True:
            await asyncio.sleep(1)
            now = datetime.now(UTC)
            for conversation_id, typers in list(self._typing.items()):
                expired_users = [
                    user_id for user_id, expires_at in typers.items() if expires_at <= now
                ]
                if not expired_users:
                    continue
                workspace_id: UUID | None = None
                for user_id in expired_users:
                    typers.pop(user_id, None)
                    connection_ids = self._conversation_connections.get(conversation_id, set())
                    for connection_id in connection_ids:
                        connection = self._connections.get(connection_id)
                        if connection and connection.workspace_id:
                            workspace_id = connection.workspace_id
                            break
                    if workspace_id:
                        await self.broadcast_conversation(
                            workspace_id,
                            conversation_id,
                            RealtimeEvent(
                                type=RealtimeEventType.TYPING_STOPPED,
                                workspace_id=workspace_id,
                                conversation_id=conversation_id,
                                payload={"user_id": str(user_id)},
                            ),
                        )

    async def run_heartbeat(self, connection_id: UUID) -> None:
        while connection_id in self._connections:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            connection = self._connections.get(connection_id)
            if connection is None:
                break
            try:
                await connection.websocket.send_json(
                    RealtimeEvent(
                        type=RealtimeEventType.PONG,
                        workspace_id=connection.workspace_id or connection.user_id,
                        payload={"heartbeat": True},
                    ).to_wire()
                )
            except (WebSocketDisconnect, RuntimeError):
                await self.disconnect(connection_id)
                break


_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager


def set_ws_manager(manager: WebSocketManager | None) -> None:
    global _manager
    _manager = manager
