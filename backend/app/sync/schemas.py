from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BranchSyncState, RepositoryProvider, RepositoryVisibility
from app.repository_branches.schemas import BranchMemoryResponse, BranchSyncRecordSummary


class SyncRepositorySummary(BaseModel):
    id: UUID
    name: str
    provider: RepositoryProvider
    owner: str
    repository_name: str
    remote_url: str
    default_branch: str
    visibility: RepositoryVisibility


class SyncRepositoryBranchSummary(BaseModel):
    id: UUID
    repository_id: UUID
    name: str
    is_default: bool
    is_active: bool


class SyncCommitSummary(BaseModel):
    id: UUID
    commit_hash: str
    title: str
    created_at: datetime


class SyncContextPackageSummary(BaseModel):
    id: UUID
    commit_id: UUID
    commit_hash: str
    version: int
    generated_at: datetime


class SyncStatusResponse(BaseModel):
    repository: SyncRepositorySummary
    repository_branch: SyncRepositoryBranchSummary
    sync_version: int
    sync_state: BranchSyncState
    latest_commit: SyncCommitSummary | None = None
    latest_context_package: SyncContextPackageSummary | None = None
    latest_sync_record: BranchSyncRecordSummary | None = None
    last_synchronized_at: datetime | None = None


class SyncPullResponse(BaseModel):
    branch_memory: BranchMemoryResponse
    latest_commit: SyncCommitSummary | None = None
    latest_context_package: SyncContextPackageSummary | None = None
    latest_sync_record: BranchSyncRecordSummary | None = None
    branch_sync_version: int


class SyncPushRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1024)
    commit_id: UUID | None = None
    context_package_id: UUID | None = None


class SyncPushResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sync_version: int
    sync_state: BranchSyncState
    latest_sync_record: BranchSyncRecordSummary
    last_synchronized_at: datetime
