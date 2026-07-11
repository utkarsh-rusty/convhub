from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PullPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repository_branch_id: UUID
    package_version: int
    generated_at: datetime
    workspace: dict[str, Any]
    project: dict[str, Any]
    repository: dict[str, Any]
    repository_branch: dict[str, Any]
    repository_memory: dict[str, Any] | None = None
    transcript_snapshot: dict[str, Any] | None = None
    latest_context_package: dict[str, Any] | None = None
    latest_commit: dict[str, Any] | None = None
    sync: dict[str, Any]
    active_developer: dict[str, Any] | None = None
    markdown_content: str = ""
    json_content: dict[str, Any] = Field(default_factory=dict)


class PullPackageExportResponse(BaseModel):
    filename: str
    content: str
    content_type: str = "text/markdown"


class PullPackageJsonExportResponse(BaseModel):
    filename: str
    content: dict[str, Any]
