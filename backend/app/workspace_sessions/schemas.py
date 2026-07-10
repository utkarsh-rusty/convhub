from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeveloperWorkspaceSessionStatus


class WorkspaceSessionCreate(BaseModel):
    repository_id: UUID
    repository_branch_id: UUID
    conversation_id: UUID
    client_name: str | None = Field(default=None, max_length=255)
    client_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=64)
    working_directory: str | None = None


class WorkspaceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    repository_id: UUID
    repository_branch_id: UUID
    conversation_id: UUID
    user_id: UUID
    status: DeveloperWorkspaceSessionStatus
    started_at: datetime
    last_heartbeat_at: datetime
    closed_at: datetime | None = None
    client_name: str | None = None
    client_version: str | None = None
    platform: str | None = None
    working_directory: str | None = None
    user_name: str | None = None
    repository_branch_name: str | None = None
    conversation_title: str | None = None
    created_at: datetime
    updated_at: datetime
