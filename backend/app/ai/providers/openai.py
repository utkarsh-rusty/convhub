from collections.abc import AsyncIterator
from decimal import Decimal

from openai import AsyncOpenAI

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse, ProviderStreamEvent


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def supports_streaming(self) -> bool:
        return True

    def _build_messages(self, prompt_context: PromptContext) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if prompt_context.system_prompt:
            messages.append({"role": "system", "content": prompt_context.system_prompt})
        for message in prompt_context.chat_messages:
            if message.role in {"user", "assistant"}:
                messages.append({"role": message.role, "content": message.content})
        return messages

    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        response = await self._client.chat.completions.create(
            model=model,
            messages=self._build_messages(prompt_context),
            max_tokens=1024,
        )
        return self._to_ai_response(response, model)

    async def stream_events(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AsyncIterator[ProviderStreamEvent]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=self._build_messages(prompt_context),
            max_tokens=1024,
            stream=True,
            stream_options={"include_usage": True},
        )

        accumulated = ""
        usage = None
        response_model = model
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    accumulated += delta
                    yield ProviderStreamEvent(delta=delta)
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.model:
                response_model = chunk.model

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        yield ProviderStreamEvent(
            response=AIResponse(
                content=accumulated.strip() or "(empty response)",
                model=response_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=_estimate_cost(input_tokens, output_tokens),
            )
        )

    def _to_ai_response(self, response, model: str) -> AIResponse:
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if not content:
            content = "(empty response)"

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return AIResponse(
            content=content,
            model=response.model or model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=_estimate_cost(input_tokens, output_tokens),
        )


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_rate = Decimal("0.0000025")
    output_rate = Decimal("0.00001")
    total = (Decimal(input_tokens) * input_rate) + (Decimal(output_tokens) * output_rate)
    return float(total)
