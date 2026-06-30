from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RealtimeEventType(str, Enum):
    MESSAGE_CREATED = "message.created"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_STREAMING = "message.streaming"
    MESSAGE_COMPLETED = "message.completed"
    TYPING_STARTED = "typing.started"
    TYPING_STOPPED = "typing.stopped"
    CONVERSATION_UPDATED = "conversation.updated"
    CREDITS_UPDATED = "credits.updated"
    ROUTING_SELECTED = "routing.selected"
    BORROW_STARTED = "borrow.started"
    BORROW_COMPLETED = "borrow.completed"
    MEMBER_JOINED = "member.joined"
    MEMBER_LEFT = "member.left"
    NOTIFICATION_CREATED = "notification.created"
    PRESENCE_UPDATED = "presence.updated"
    CONNECTED = "connected"
    PONG = "pong"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    type: RealtimeEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    workspace_id: UUID
    conversation_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "workspace_id": str(self.workspace_id),
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "payload": self.payload,
        }
