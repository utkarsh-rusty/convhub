from app.ai.prompt_builder import PromptContext
from app.ai.providers.base import AIProvider, AIResponse


class MockProvider(AIProvider):
    async def generate(
        self,
        prompt_context: PromptContext,
        model: str,
    ) -> AIResponse:
        last_user = next(
            (message for message in reversed(prompt_context.chat_messages) if message.role == "user"),
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
