from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.schemas import ChatSendRequest
from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import MessageCreate, MessageResponse
from app.conversations.service import ConversationService
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.message import Message


class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        conversation_service: ConversationService,
        gateway: AIGateway,
    ) -> None:
        self.db = db
        self.conversation_service = conversation_service
        self.gateway = gateway

    async def send(self, data: ChatSendRequest, ctx: WorkspaceContext) -> MessageResponse:
        conversation = await self._get_conversation(
            data.conversation_id,
            ctx.workspace_id,
            ctx.user.id,
        )
        if conversation.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is archived",
            )

        user_message_response = await self.conversation_service.create_message(
            conversation,
            ctx.user,
            MessageCreate(content=data.content),
        )

        user_message = await self._get_message(user_message_response.id)
        history = await self._list_messages(conversation.id)

        conversation = await self._get_conversation(
            data.conversation_id,
            ctx.workspace_id,
            ctx.user.id,
        )
        return await self.gateway.generate(conversation, user_message, history)

    async def _get_conversation(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    async def _get_message(self, message_id: UUID) -> Message:
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()
        if message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        return message

    async def _list_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
