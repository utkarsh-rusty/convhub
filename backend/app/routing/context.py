from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.ai.prompt_builder import PromptContext
from app.models.conversation import Conversation
from app.models.user import User
from app.models.workspace import Workspace


@dataclass(frozen=True)
class RoutingContext:
    workspace: Workspace
    requesting_user: User
    conversation: Conversation
    provider: str | None
    model: str | None
    estimated_cost: Decimal
    prompt_context: PromptContext | None = field(default=None)
