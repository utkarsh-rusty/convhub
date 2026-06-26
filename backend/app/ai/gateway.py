from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import AIProvider, ChatMessage
from app.ai.providers.mock import MockProvider
from app.conversations.schemas import MessageResponse
from app.core.config import Settings
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.enums import AIRequestStatus, MessageRole
from app.models.message import Message


class AIGateway:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._provider = _create_provider(settings)

    async def generate(
        self,
        conversation: Conversation,
        user_message: Message,
        history: list[Message],
    ) -> MessageResponse:
        started_at = datetime.now(UTC)
        provider_name = self.settings.ai_provider
        model_name = self.settings.ai_model

        ai_request = AIRequest(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            provider=provider_name,
            model=model_name,
            status=AIRequestStatus.PENDING,
            started_at=started_at,
        )
        self.db.add(ai_request)

        try:
            response = await self._provider.generate(
                messages=_to_chat_messages(history),
                system_prompt=self.settings.ai_system_prompt,
            )

            completed_at = datetime.now(UTC)
            latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            assistant_message = Message(
                conversation_id=conversation.id,
                author_id=None,
                role=MessageRole.ASSISTANT,
                content=response.content,
            )
            self.db.add(assistant_message)
            await self.db.flush()

            conversation.last_activity_at = completed_at
            ai_request.assistant_message_id = assistant_message.id
            ai_request.status = AIRequestStatus.COMPLETED
            ai_request.completed_at = completed_at
            ai_request.latency_ms = latency_ms
            ai_request.model = response.model
            ai_request.input_tokens = response.input_tokens
            ai_request.output_tokens = response.output_tokens
            ai_request.estimated_cost = (
                Decimal(str(response.estimated_cost))
                if response.estimated_cost is not None
                else None
            )

            await self.db.commit()
            await self.db.refresh(assistant_message)
            return MessageResponse.model_validate(assistant_message)
        except Exception as exc:
            completed_at = datetime.now(UTC)
            latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            ai_request.status = AIRequestStatus.FAILED
            ai_request.completed_at = completed_at
            ai_request.latency_ms = latency_ms
            ai_request.error_message = str(exc)

            await self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI provider failed to generate a response",
            ) from exc


def _create_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(settings)
    return MockProvider()


def _to_chat_messages(messages: list[Message]) -> list[ChatMessage]:
    return [
        ChatMessage(role=message.role.value, content=message.content)
        for message in messages
        if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
    ]
