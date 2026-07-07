from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RepositoryProvider, RepositoryVisibility


class RepositoryCreate(BaseModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=255)
    provider: RepositoryProvider
    owner: str = Field(min_length=1, max_length=255)
    repository_name: str = Field(min_length=1, max_length=255)
    remote_url: str = Field(min_length=1, max_length=2048)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    visibility: RepositoryVisibility = RepositoryVisibility.PRIVATE
    is_active: bool = True


class RepositoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider: RepositoryProvider | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    repository_name: str | None = Field(default=None, min_length=1, max_length=255)
    remote_url: str | None = Field(default=None, min_length=1, max_length=2048)
    default_branch: str | None = Field(default=None, min_length=1, max_length=255)
    visibility: RepositoryVisibility | None = None
    is_active: bool | None = None


class RepositoryConversationSummary(BaseModel):
    id: UUID
    title: str
    branch_name: str | None = None
    parent_conversation_id: UUID | None = None
    last_activity_at: datetime
    message_count: int = 0
    commit_count: int = 0


class RepositorySummary(BaseModel):
    id: UUID
    name: str
    provider: RepositoryProvider
    owner: str
    repository_name: str
    remote_url: str
    default_branch: str
    visibility: RepositoryVisibility
    sync_status: str = "not_synced"


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    name: str
    provider: RepositoryProvider
    owner: str
    repository_name: str
    remote_url: str
    default_branch: str
    visibility: RepositoryVisibility
    is_active: bool
    created_by_id: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    conversation_count: int = 0
    sync_status: str = "not_synced"
    latest_commit: str | None = None
    connected_conversations: list[RepositoryConversationSummary] = Field(default_factory=list)


class RepositoryAttachCreateRepository(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: RepositoryProvider
    owner: str = Field(min_length=1, max_length=255)
    repository_name: str = Field(min_length=1, max_length=255)
    remote_url: str = Field(min_length=1, max_length=2048)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    visibility: RepositoryVisibility = RepositoryVisibility.PRIVATE
    is_active: bool = True


class RepositoryAttachRequest(BaseModel):
    repository_id: UUID | None = None
    create_repository: RepositoryAttachCreateRepository | None = None

    @model_validator(mode="after")
    def validate_repository_options(self) -> Self:
        if self.repository_id is not None and self.create_repository is not None:
            raise ValueError("Provide either repository_id or create_repository, not both")
        if self.repository_id is None and self.create_repository is None:
            raise ValueError("Provide either repository_id or create_repository")
        return self
