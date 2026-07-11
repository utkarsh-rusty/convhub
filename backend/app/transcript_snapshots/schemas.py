from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TranscriptSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_ai_session_id: UUID
    snapshot_version: int
    character_count: int
    created_at: datetime
    updated_at: datetime


class TranscriptSnapshotExportResponse(BaseModel):
    filename: str
    content: str
    content_type: str = "text/markdown"
    snapshot_version: int
    character_count: int
