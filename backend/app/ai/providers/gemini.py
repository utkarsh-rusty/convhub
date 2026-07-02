from __future__ import annotations

import json
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import httpx

from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse, ProviderStreamEvent

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def supports_streaming(self) -> bool:
        return True

    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        payload = self._build_payload(prompt_context)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GEMINI_API_BASE}/models/{model}:generateContent",
                params={"key": self._api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return self._to_ai_response(data, model)

    async def stream_events(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AsyncIterator[ProviderStreamEvent]:
        payload = self._build_payload(prompt_context)
        accumulated = ""
        usage_metadata: dict[str, Any] | None = None

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{GEMINI_API_BASE}/models/{model}:streamGenerateContent",
                params={"key": self._api_key, "alt": "sse"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if not raw or raw == "[DONE]":
                        continue
                    chunk = json.loads(raw)
                    text = _extract_text(chunk)
                    if text:
                        accumulated += text
                        yield ProviderStreamEvent(delta=text)
                    if "usageMetadata" in chunk:
                        usage_metadata = chunk["usageMetadata"]

        yield ProviderStreamEvent(
            response=AIResponse(
                content=accumulated.strip() or "(empty response)",
                model=model,
                input_tokens=int((usage_metadata or {}).get("promptTokenCount", 0)),
                output_tokens=int((usage_metadata or {}).get("candidatesTokenCount", 0)),
                estimated_cost=_estimate_cost(
                    int((usage_metadata or {}).get("promptTokenCount", 0)),
                    int((usage_metadata or {}).get("candidatesTokenCount", 0)),
                ),
            )
        )

    def _build_payload(self, prompt_context: PromptContext) -> dict[str, Any]:
        contents: list[dict[str, Any]] = []
        for message in prompt_context.chat_messages:
            if message.role not in {"user", "assistant"}:
                continue
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        payload: dict[str, Any] = {"contents": contents}
        if prompt_context.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": prompt_context.system_prompt}]}
        return payload

    def _to_ai_response(self, data: dict[str, Any], model: str) -> AIResponse:
        content = _extract_text(data).strip()
        if not content:
            content = "(empty response)"

        usage = data.get("usageMetadata", {})
        input_tokens = int(usage.get("promptTokenCount", 0))
        output_tokens = int(usage.get("candidatesTokenCount", 0))

        return AIResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=_estimate_cost(input_tokens, output_tokens),
        )


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(str(part.get("text", "")) for part in parts)


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_rate = Decimal("0.00000125")
    output_rate = Decimal("0.000005")
    total = (Decimal(input_tokens) * input_rate) + (Decimal(output_tokens) * output_rate)
    return float(total)
