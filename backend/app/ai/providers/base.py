from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.prompt_builder import PromptContext


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class AIResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float | None = None


class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        """Generate an assistant reply from a provider-ready prompt context."""
