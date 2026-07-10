from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BranchMemorySyncStatus, BranchSyncType


class RepositoryBranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_default: bool = False


class RepositoryBranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class BranchSyncRecordSummary(BaseModel):
    id: UUID
    branch_memory_id: UUID
    conversation_id: UUID | None = None
    convhub_branch_id: UUID | None = None
    commit_id: UUID | None = None
    context_package_id: UUID | None = None
    user_id: UUID | None = None
    user_name: str | None = None
    sync_type: BranchSyncType
    sync_version: int
    notes: str | None = None
    conversation_title: str | None = None
    convhub_branch_name: str | None = None
    commit_hash: str | None = None
    context_package_version: int | None = None
    created_at: datetime


class BranchMemorySummary(BaseModel):
    id: UUID
    repository_branch_id: UUID
    latest_sync_record_id: UUID | None = None
    current_conversation_id: UUID | None = None
    current_convhub_branch_id: UUID | None = None
    current_commit_id: UUID | None = None
    current_context_package_id: UUID | None = None
    working_user_id: UUID | None = None
    working_user_name: str | None = None
    memory_version: int
    current_sync_version: int
    last_sync_at: datetime | None = None
    sync_status: BranchMemorySyncStatus
    current_conversation_title: str | None = None
    current_convhub_branch_name: str | None = None
    current_commit_hash: str | None = None
    current_context_package_version: int | None = None
    latest_sync_record: BranchSyncRecordSummary | None = None


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
    latest_sync_record_id: UUID | None = None
    current_conversation_id: UUID | None = None
    current_convhub_branch_id: UUID | None = None
    current_commit_id: UUID | None = None
    current_context_package_id: UUID | None = None
    working_user_id: UUID | None = None
    working_user_name: str | None = None
    memory_version: int
    current_sync_version: int
    last_sync_at: datetime | None = None
    sync_status: BranchMemorySyncStatus
    current_conversation_title: str | None = None
    current_convhub_branch_name: str | None = None
    current_commit_hash: str | None = None
    current_context_package_version: int | None = None
    latest_sync_record: BranchSyncRecordSummary | None = None
    created_at: datetime
    updated_at: datetime


class BranchMemoryExportResponse(BaseModel):
    filename: str
    content: dict


class BranchSyncRecordResponse(BranchSyncRecordSummary):
    repository_branch_id: UUID
    repository_id: UUID
    repository_branch_name: str


class BranchSyncHistoryExportResponse(BaseModel):
    filename: str
    content: dict
