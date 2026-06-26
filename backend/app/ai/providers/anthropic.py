from decimal import Decimal

from anthropic import AsyncAnthropic

from app.ai.providers.base import AIProvider, AIResponse, ChatMessage
from app.core.config import Settings


class AnthropicProvider(AIProvider):
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_PROVIDER=anthropic")

        self._settings = settings
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None,
    ) -> AIResponse:
        response = await self._client.messages.create(
            model=self._settings.ai_model,
            max_tokens=1024,
            system=system_prompt or "",
            messages=[
                {"role": message.role, "content": message.content}
                for message in messages
                if message.role in {"user", "assistant"}
            ],
        )

        content_blocks = [block.text for block in response.content if block.type == "text"]
        content = "\n".join(content_blocks).strip()
        if not content:
            content = "(empty response)"

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return AIResponse(
            content=content,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=_estimate_cost(input_tokens, output_tokens),
        )


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_rate = Decimal("0.000003")
    output_rate = Decimal("0.000015")
    total = (Decimal(input_tokens) * input_rate) + (Decimal(output_tokens) * output_rate)
    return float(total)
