from collections.abc import AsyncIterator
from decimal import Decimal

from anthropic import AsyncAnthropic

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse, ProviderStreamEvent


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    @property
    def supports_streaming(self) -> bool:
        return True

    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        response = await self._client.messages.create(
            model=model,
            max_tokens=1024,
            system=prompt_context.system_prompt,
            messages=[
                {"role": message.role, "content": message.content}
                for message in prompt_context.chat_messages
                if message.role in {"user", "assistant"}
            ],
        )

        return self._to_ai_response(response)

    async def stream_events(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AsyncIterator[ProviderStreamEvent]:
        async with self._client.messages.stream(
            model=model,
            max_tokens=1024,
            system=prompt_context.system_prompt,
            messages=[
                {"role": message.role, "content": message.content}
                for message in prompt_context.chat_messages
                if message.role in {"user", "assistant"}
            ],
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield ProviderStreamEvent(delta=text)
            final = await stream.get_final_message()

        yield ProviderStreamEvent(response=self._to_ai_response(final))

    def _to_ai_response(self, response) -> AIResponse:
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
