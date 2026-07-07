from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.conversation import DEFAULT_CONVERSATION_TITLE
from app.models.enums import (
    ConversationParticipantRole,
    ExecutionType,
    MessageRole,
    RoutingPolicyType,
)
from app.repositories.schemas import RepositorySummary


class ConversationParticipantSummary(BaseModel):
    user_id: UUID
    name: str
    role: ConversationParticipantRole


class ConversationCreate(BaseModel):
    title: str = Field(default=DEFAULT_CONVERSATION_TITLE, min_length=1, max_length=255)
    project_id: UUID | None = None


class EnableCodingRequest(BaseModel):
    """Enable coding workspace without repository attachment."""


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ConversationOwnerSummary(BaseModel):
    user_id: UUID
    name: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    coding_enabled: bool = False
    repository_id: UUID | None = None
    repository: RepositorySummary | None = None
    created_by_id: UUID | None
    owner_id: UUID
    owner: ConversationOwnerSummary | None = None
    owner_name: str | None = None
    created_by_name: str | None = None
    title: str
    last_activity_at: datetime
    latest_activity_at: datetime | None = None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    parent_conversation_id: UUID | None = None
    branch_from_message_id: UUID | None = None
    branch_name: str | None = None
    is_participant: bool = False
    participant_count: int = 0
    message_count: int = 0
    ai_request_count: int = 0
    commit_count: int = 0
    participants: list[ConversationParticipantSummary] = Field(default_factory=list)
    is_restored: bool = False
    restored_from_package_id: UUID | None = None
    restored_from_commit_id: UUID | None = None
    restored_from_conversation_id: UUID | None = None
    restored_by_user_id: UUID | None = None
    restored_at: datetime | None = None
    restored_from_commit_hash: str | None = None


class BranchTreeNode(BaseModel):
    id: UUID
    title: str
    branch_name: str | None = None
    parent_conversation_id: UUID | None = None
    owner_id: UUID
    owner_name: str | None = None
    latest_activity_at: datetime
    message_count: int = 0
    participant_count: int = 0
    commit_count: int = 0
    commits_ahead: int = 0
    commits_behind: int = 0
    common_ancestor_commit_hash: str | None = None
    archived_at: datetime | None = None
    is_participant: bool = False
    is_owned_by_viewer: bool = False
    created_at: datetime | None = None
    children: list["BranchTreeNode"] = Field(default_factory=list)


class BranchTreeResponse(BaseModel):
    root: BranchTreeNode


class BranchManagerResponse(BaseModel):
    root: BranchTreeNode
    total_branches: int = 0
    total_commits: int = 0
    total_messages: int = 0
    total_participants: int = 0


class CommitGraphNode(BaseModel):
    commit_hash: str
    title: str
    description: str | None = None
    author_id: UUID
    author_name: str
    created_at: datetime
    conversation_id: UUID
    branch_name: str | None = None
    conversation_title: str
    parent_commit_hash: str | None = None
    latest_message_id: UUID
    providers: list[str] = Field(default_factory=list)
    credits_used: str = "0"
    borrowed_requests: int = 0


class CommitGraphEdge(BaseModel):
    source: str
    target: str


class CommitGraphResponse(BaseModel):
    nodes: list[CommitGraphNode] = Field(default_factory=list)
    edges: list[CommitGraphEdge] = Field(default_factory=list)


class BranchFamilyOverviewResponse(BaseModel):
    root_id: UUID
    total_commits: int = 0
    total_branches: int = 0
    total_participants: int = 0
    total_messages: int = 0
    ai_request_count: int = 0
    latest_activity: datetime | None = None
    providers_used: list[str] = Field(default_factory=list)
    credits_used: str = "0"


class CommitSearchResult(BaseModel):
    commit_hash: str
    title: str
    description: str | None = None
    author_name: str
    created_at: datetime
    conversation_id: UUID
    branch_name: str | None = None
    latest_message_id: UUID
    providers: list[str] = Field(default_factory=list)
    match_reason: str


class CommitSearchResponse(BaseModel):
    conversation_id: UUID
    query: str
    results: list[CommitSearchResult] = Field(default_factory=list)


class ComparisonMessage(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    author_id: UUID | None = None


class ConversationCompareResponse(BaseModel):
    left_id: UUID
    right_id: UUID
    common_ancestor_id: UUID | None = None
    shared_messages: list[ComparisonMessage] = Field(default_factory=list)
    left_only: list[ComparisonMessage] = Field(default_factory=list)
    right_only: list[ComparisonMessage] = Field(default_factory=list)
    divergence_message_id: UUID | None = None


class TimelineEvent(BaseModel):
    event_type: str
    occurred_at: datetime
    actor_id: UUID | None = None
    actor_name: str | None = None
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationTimelineResponse(BaseModel):
    conversation_id: UUID
    events: list[TimelineEvent] = Field(default_factory=list)


class ConversationStatsResponse(BaseModel):
    conversation_id: UUID
    message_count: int
    assistant_messages: int
    user_messages: int
    participants: int
    providers_used: list[str] = Field(default_factory=list)
    borrowed_requests: int
    credits_used: str
    latest_activity: datetime


class SearchMessageMatch(BaseModel):
    message: ComparisonMessage
    context_before: list[ComparisonMessage] = Field(default_factory=list)
    context_after: list[ComparisonMessage] = Field(default_factory=list)


class SearchCommitMatch(BaseModel):
    commit_hash: str
    title: str
    description: str | None = None
    created_by_name: str
    created_at: datetime
    latest_message_id: UUID


class ConversationSearchResponse(BaseModel):
    conversation_id: UUID
    query: str
    matches: list[SearchMessageMatch] = Field(default_factory=list)
    commit_matches: list[SearchCommitMatch] = Field(default_factory=list)


class CommitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    latest_message_id: UUID


class CommitListItem(BaseModel):
    commit_hash: str
    title: str
    description: str | None = None
    created_by_id: UUID
    created_by_name: str
    created_at: datetime
    latest_message_id: UUID
    parent_commit_id: UUID | None = None
    parent_commit_hash: str | None = None


class CommitMessageSummary(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    author_id: UUID | None = None


class CommitRangeMetadata(BaseModel):
    providers: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    execution_types: list[str] = Field(default_factory=list)
    routing_policies: list[str] = Field(default_factory=list)
    credits_used: str = "0"
    borrowed_requests: int = 0
    borrowed_from: list[str] = Field(default_factory=list)


class CommitDetailResponse(BaseModel):
    id: UUID
    commit_hash: str
    title: str
    description: str | None = None
    conversation_id: UUID
    conversation_title: str
    workspace_id: UUID
    checkpoint_id: UUID
    latest_message_id: UUID
    parent_commit_id: UUID | None = None
    parent_commit_hash: str | None = None
    child_commit_hashes: list[str] = Field(default_factory=list)
    created_by_id: UUID
    created_by_name: str
    created_at: datetime
    message: CommitMessageSummary
    range_metadata: CommitRangeMetadata
    context_package_id: UUID | None = None


class ContextPackageListItem(BaseModel):
    id: UUID
    commit_id: UUID
    commit_hash: str
    commit_title: str
    conversation_id: UUID
    version: int
    status: str
    generated_at: datetime


class ContextPackageResponse(BaseModel):
    id: UUID
    commit_id: UUID
    conversation_id: UUID
    version: int
    status: str
    generated_at: datetime
    metadata: dict[str, Any]
    summary: dict[str, Any]
    statistics: dict[str, Any]
    search_keywords: list[Any] = Field(default_factory=list)


class ContextPackageExportResponse(BaseModel):
    id: UUID
    commit_id: UUID
    conversation_id: UUID
    version: int
    status: str
    generated_at: datetime
    metadata: dict[str, Any]
    summary: dict[str, Any]
    statistics: dict[str, Any]
    search_keywords: list[Any] = Field(default_factory=list)


class ContextRestoreRequest(BaseModel):
    conversation_name: str | None = Field(default=None, max_length=255)
    project_id: UUID | None = None
    restore_participants: bool = True
    restore_messages: bool = True
    restore_metadata: bool = True
    restore_only_self: bool = False


class ConversationRestoreInfoResponse(BaseModel):
    conversation_id: UUID
    is_restored: bool
    restored_at: datetime | None = None
    restored_by_user_id: UUID | None = None
    restored_by_name: str | None = None
    original_conversation_id: UUID | None = None
    original_conversation_title: str | None = None
    original_commit_id: UUID | None = None
    original_commit_hash: str | None = None
    original_commit_title: str | None = None
    context_package_id: UUID | None = None
    context_package_version: int | None = None
    context_package_status: str | None = None


class ConversationBranchCreate(BaseModel):
    message_id: UUID
    branch_name: str | None = Field(default=None, max_length=255)


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    branch_name: str | None = None
    parent_conversation_id: UUID | None = None
    branch_from_message_id: UUID | None = None
    created_at: datetime
    last_activity_at: datetime


class ConversationLineageResponse(BaseModel):
    root: ConversationSummary
    ancestors: list[ConversationSummary] = Field(default_factory=list)
    current: ConversationSummary


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


class ExecutionSummary(BaseModel):
    provider: str
    model: str
    owner_name: str | None = None
    execution_type: ExecutionType
    routing_policy: RoutingPolicyType
    borrowed_from: str | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    author_id: UUID | None
    role: MessageRole
    content: str
    created_at: datetime
    provider: str | None = None
    execution: ExecutionSummary | None = None
    budget_warning: str | None = None
