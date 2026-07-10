from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import BranchSyncState, DeveloperWorkspaceSessionStatus
from app.repository_branches.schemas import BranchMemoryResponse
from app.sync.schemas import SyncCommitSummary, SyncContextPackageSummary


class WorkspaceClientConnectRequest(BaseModel):
    repository_id: UUID
    repository_branch_id: UUID
    conversation_id: UUID
    client_name: str = Field(min_length=1, max_length=255)
    client_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=64)


class WorkspaceClientConnectResponse(BaseModel):
    workspace_session_id: UUID
    sync_state: BranchSyncState
    current_branch_version: int
    current_memory_version: int
    resumed: bool = False
    session_status: DeveloperWorkspaceSessionStatus


class WorkspaceClientHeartbeatRequest(BaseModel):
    workspace_session_id: UUID


class WorkspaceClientHeartbeatResponse(BaseModel):
    workspace_session_id: UUID
    status: DeveloperWorkspaceSessionStatus
    last_heartbeat_at: datetime


class WorkspaceClientPushRequest(BaseModel):
    workspace_session_id: UUID
    latest_commit_id: UUID | None = None
    latest_context_package_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1024)


class WorkspaceClientPushResponse(BaseModel):
    workspace_session_id: UUID
    sync_version: int
    sync_state: BranchSyncState
    last_synchronized_at: datetime | None = None


class WorkspaceClientPullResponse(BaseModel):
    workspace_session_id: UUID
    branch_memory: BranchMemoryResponse
    latest_commit: SyncCommitSummary | None = None
    latest_context_package: SyncContextPackageSummary | None = None
    sync_version: int
    branch_version: int
    active_developer: str | None = None
    sync_state: BranchSyncState


class WorkspaceClientDisconnectRequest(BaseModel):
    workspace_session_id: UUID


class WorkspaceClientDisconnectResponse(BaseModel):
    workspace_session_id: UUID
    status: DeveloperWorkspaceSessionStatus
    closed_at: datetime | None = None


class WorkspaceClientProtocolStatusResponse(BaseModel):
    plugin_protocol_ready: bool = True
    connected_sessions: int
    current_sync_version: int | None = None
    repository_id: UUID
