from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BranchMemorySyncStatus


class RepositoryBranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_default: bool = False


class RepositoryBranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class BranchMemorySummary(BaseModel):
    id: UUID
    repository_branch_id: UUID
    current_conversation_id: UUID | None = None
    current_convhub_branch_id: UUID | None = None
    current_commit_id: UUID | None = None
    current_context_package_id: UUID | None = None
    working_user_id: UUID | None = None
    working_user_name: str | None = None
    memory_version: int
    sync_status: BranchMemorySyncStatus
    last_push_at: datetime | None = None
    last_pull_at: datetime | None = None
    current_conversation_title: str | None = None
    current_convhub_branch_name: str | None = None
    current_commit_hash: str | None = None
    current_context_package_version: int | None = None


class RepositoryBranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    name: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    memory: BranchMemorySummary | None = None


class BranchMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_branch_id: UUID
    repository_id: UUID
    repository_branch_name: str
    current_conversation_id: UUID | None = None
    current_convhub_branch_id: UUID | None = None
    current_commit_id: UUID | None = None
    current_context_package_id: UUID | None = None
    working_user_id: UUID | None = None
    working_user_name: str | None = None
    memory_version: int
    sync_status: BranchMemorySyncStatus
    last_push_at: datetime | None = None
    last_pull_at: datetime | None = None
    current_conversation_title: str | None = None
    current_convhub_branch_name: str | None = None
    current_commit_hash: str | None = None
    current_context_package_version: int | None = None
    created_at: datetime
    updated_at: datetime


class BranchMemoryExportResponse(BaseModel):
    filename: str
    content: dict
