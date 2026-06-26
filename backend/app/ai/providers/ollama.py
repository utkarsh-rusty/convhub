import time

import httpx

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        ollama_messages: list[dict[str, str]] = []
        if prompt_context.system_prompt:
            ollama_messages.append({"role": "system", "content": prompt_context.system_prompt})

        for message in prompt_context.chat_messages:
            if message.role in {"user", "assistant", "system"}:
                ollama_messages.append({"role": message.role, "content": message.content})

        started_at = time.monotonic()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()

        _ = int((time.monotonic() - started_at) * 1000)

        message = payload.get("message", {})
        content = str(message.get("content", "")).strip()
        if not content:
            content = "(empty response)"

        return AIResponse(
            content=content,
            model=str(payload.get("model", model)),
            input_tokens=0,
            output_tokens=0,
            estimated_cost=0.0,
        )

    async def test_connection(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
