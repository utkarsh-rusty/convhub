from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_branch_id: UUID
    repository_id: UUID
    repository_branch_name: str
    memory_version: int
    latest_commit_id: UUID | None = None
    latest_commit_hash: str | None = None
    latest_context_package_id: UUID | None = None
    latest_context_package_version: int | None = None
    latest_workspace_session_id: UUID | None = None
    generated_at: datetime
    markdown_content: str
    json_content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RepositoryMemoryExportResponse(BaseModel):
    filename: str
    content: str
    content_type: str = "text/markdown"


class RepositoryMemoryJsonExportResponse(BaseModel):
    filename: str
    content: dict[str, Any]
