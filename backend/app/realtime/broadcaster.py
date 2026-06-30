from __future__ import annotations

from typing import Any
from uuid import UUID

from app.realtime.events import RealtimeEvent, RealtimeEventType
from app.realtime.manager import WebSocketManager, get_ws_manager


class RealtimeBroadcaster:
    def __init__(self, manager: WebSocketManager) -> None:
        self._manager = manager

    async def emit(
        self,
        event_type: RealtimeEventType,
        *,
        workspace_id: UUID,
        conversation_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> None:
        event = RealtimeEvent(
            type=event_type,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload or {},
        )
        if conversation_id is not None:
            await self._manager.broadcast_conversation(workspace_id, conversation_id, event)
        else:
            await self._manager.broadcast_workspace(workspace_id, event)
        if user_id is not None:
            await self._manager.broadcast_user(user_id, event)

    async def message_created(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.MESSAGE_CREATED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def message_streaming(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.MESSAGE_STREAMING,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def message_completed(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.MESSAGE_COMPLETED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def conversation_updated(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.CONVERSATION_UPDATED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def credits_updated(
        self,
        workspace_id: UUID,
        user_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.CREDITS_UPDATED,
            workspace_id=workspace_id,
            payload=payload,
            user_id=user_id,
        )

    async def routing_selected(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.ROUTING_SELECTED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def borrow_started(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.BORROW_STARTED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )

    async def borrow_completed(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        await self.emit(
            RealtimeEventType.BORROW_COMPLETED,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
        )


def get_broadcaster() -> RealtimeBroadcaster | None:
    try:
        return RealtimeBroadcaster(get_ws_manager())
    except Exception:
        return None
