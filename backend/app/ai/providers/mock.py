from app.ai.providers.base import AIProvider, AIResponse, ChatMessage


class MockProvider(AIProvider):
    async def generate(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None,
    ) -> AIResponse:
        last_user = next((message for message in reversed(messages) if message.role == "user"), None)
        prompt_preview = last_user.content if last_user else "your message"
        content = f"[mock] Thanks for your message: {prompt_preview}"

        return AIResponse(
            content=content,
            model="mock",
            input_tokens=42,
            output_tokens=24,
            estimated_cost=0.0,
        )
