from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
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


@dataclass
class ProviderStreamEvent:
    delta: str = ""
    response: AIResponse | None = None


class AIProvider(ABC):
    @property
    def supports_streaming(self) -> bool:
        return False

    @abstractmethod
    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        """Generate an assistant reply from a provider-ready prompt context."""

    async def stream_events(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AsyncIterator[ProviderStreamEvent]:
        response = await self.generate(prompt_context, model)
        yield ProviderStreamEvent(delta=response.content, response=response)
