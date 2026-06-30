from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClientSubscribe(BaseModel):
    action: str = "subscribe"
    workspace_id: UUID
    conversation_ids: list[UUID] = Field(default_factory=list)


class ClientTyping(BaseModel):
    action: str
    conversation_id: UUID


class ClientPing(BaseModel):
    action: str = "ping"


class PresencePayload(BaseModel):
    user_id: UUID
    user_name: str
    status: str
    last_seen: str | None = None
