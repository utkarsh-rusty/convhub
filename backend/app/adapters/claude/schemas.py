from __future__ import annotations

from pydantic import BaseModel


class ClaudeHandoffResponse(BaseModel):
    """Optional JSON wrapper for tooling; primary API returns raw text/markdown."""

    filename: str
    content: str
    content_type: str = "text/markdown"
