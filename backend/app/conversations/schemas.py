from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.conversation import DEFAULT_CONVERSATION_TITLE
from app.models.enums import ConversationParticipantRole, MessageRole


class ConversationParticipantSummary(BaseModel):
    user_id: UUID
    name: str
    role: ConversationParticipantRole


class ConversationCreate(BaseModel):
    title: str = Field(default=DEFAULT_CONVERSATION_TITLE, min_length=1, max_length=255)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by_id: UUID | None
    title: str
    last_activity_at: datetime
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    participant_count: int = 0
    participants: list[ConversationParticipantSummary] = Field(default_factory=list)


class ConversationParticipantCreate(BaseModel):
    user_ids: list[UUID] = Field(min_length=1)


class ConversationParticipantResponse(BaseModel):
    conversation_id: UUID
    user_id: UUID
    name: str
    email: EmailStr
    role: ConversationParticipantRole
    joined_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    role: MessageRole = MessageRole.USER


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    author_id: UUID | None
    role: MessageRole
    content: str
    created_at: datetime
    provider: str | None = None
