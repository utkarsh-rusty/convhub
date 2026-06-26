from abc import ABC, abstractmethod
from dataclasses import dataclass


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
        messages: list[ChatMessage],
        system_prompt: str | None,
    ) -> AIResponse:
        """Generate an assistant reply from conversation history."""
