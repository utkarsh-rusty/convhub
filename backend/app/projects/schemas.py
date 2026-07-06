from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)


class ProjectMemberSummary(BaseModel):
    user_id: UUID
    name: str
    email: str
    role: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    created_by_id: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    is_default: bool = False
    conversation_count: int = 0
    branch_count: int = 0
    commit_count: int = 0
    context_package_count: int = 0
    last_activity_at: datetime | None = None
    members: list[ProjectMemberSummary] = Field(default_factory=list)
    recent_conversations: list["ProjectConversationSummary"] = Field(default_factory=list)


class ProjectConversationSummary(BaseModel):
    id: UUID
    title: str
    branch_name: str | None = None
    parent_conversation_id: UUID | None = None
    last_activity_at: datetime
    message_count: int = 0
    commit_count: int = 0
    is_restored: bool = False


ProjectResponse.model_rebuild()
