from uuid import UUID

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    conversation_id: UUID
    content: str = Field(min_length=1)
