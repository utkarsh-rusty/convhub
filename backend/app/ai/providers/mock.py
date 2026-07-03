import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse, ProviderStreamEvent


class MockProvider(AIProvider):
    @property
    def supports_streaming(self) -> bool:
        return True

    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        last_user = next(
            (
                message
                for message in reversed(prompt_context.chat_messages)
                if message.role == "user"
            ),
            None,
        )
        prompt_preview = last_user.content if last_user else "your message"
        content = f"[mock] Thanks for your message: {prompt_preview}"

        return AIResponse(
            content=content,
            model=model,
            input_tokens=42,
            output_tokens=24,
            estimated_cost=0.0,
        )

    async def stream_events(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AsyncIterator[ProviderStreamEvent]:
        response = await self.generate(prompt_context, model)
        words = response.content.split(" ")
        accumulated = ""
        for index, word in enumerate(words):
            piece = (" " if index else "") + word
            accumulated += piece
            yield ProviderStreamEvent(delta=piece)
            await asyncio.sleep(0.02)
        yield ProviderStreamEvent(response=replace(response, content=accumulated))
