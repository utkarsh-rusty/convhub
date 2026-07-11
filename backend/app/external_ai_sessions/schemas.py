from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExternalAIProvider, ExternalAISessionStatus


class ExternalAISessionConnectRequest(BaseModel):
    provider: ExternalAIProvider
    repository_id: UUID
    repository_branch_id: UUID
    conversation_id: UUID | None = None
    machine_identifier: str = Field(min_length=1, max_length=255)


class ExternalAISessionUploadRequest(BaseModel):
    session_id: UUID
    sequence_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    raw_content: str = Field(min_length=1)


class ExternalAISessionDisconnectRequest(BaseModel):
    session_id: UUID


class TranscriptChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_ai_session_id: UUID
    sequence_number: int
    start_offset: int
    end_offset: int
    raw_content: str
    created_at: datetime


class ExternalAISessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: ExternalAIProvider
    repository_id: UUID
    repository_branch_id: UUID
    conversation_id: UUID | None = None
    workspace_user_id: UUID
    machine_identifier: str
    started_at: datetime
    ended_at: datetime | None = None
    last_synced_offset: int
    status: ExternalAISessionStatus
    chunk_count: int = 0
    last_activity_at: datetime | None = None
    developer_name: str | None = None
    repository_branch_name: str | None = None
    created_at: datetime
    updated_at: datetime
