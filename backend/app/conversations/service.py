from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.models.conversation import DEFAULT_CONVERSATION_TITLE, Conversation
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(
        self,
        ctx: WorkspaceContext,
        data: ConversationCreate,
    ) -> ConversationResponse:
        now = datetime.now(UTC)
        conversation = Conversation(
            workspace_id=ctx.workspace_id,
            created_by_id=ctx.user.id,
            title=data.title or DEFAULT_CONVERSATION_TITLE,
            last_activity_at=now,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def list_conversations(self, workspace_id: UUID) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        return [ConversationResponse.model_validate(c) for c in result.scalars().all()]

    async def get_conversation(self, conversation: Conversation) -> ConversationResponse:
        return ConversationResponse.model_validate(conversation)

    async def update_conversation(
        self,
        conversation: Conversation,
        data: ConversationUpdate,
    ) -> ConversationResponse:
        if data.title is not None:
            conversation.title = data.title

        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def delete_conversation(self, conversation: Conversation) -> None:
        if conversation.archived_at is None:
            conversation.archived_at = datetime.now(UTC)
            await self.db.commit()

    async def archive_conversation(self, conversation: Conversation) -> ConversationResponse:
        if conversation.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is already archived",
            )
        conversation.archived_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def restore_conversation(self, conversation: Conversation) -> ConversationResponse:
        if conversation.archived_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not archived",
            )
        conversation.archived_at = None
        conversation.last_activity_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def create_message(
        self,
        conversation: Conversation,
        user: User,
        data: MessageCreate,
    ) -> MessageResponse:
        if data.role != MessageRole.USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only user messages can be created via the API",
            )

        now = datetime.now(UTC)
        message = Message(
            conversation_id=conversation.id,
            author_id=user.id,
            role=MessageRole.USER,
            content=data.content,
        )
        conversation.last_activity_at = now
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return MessageResponse.model_validate(message)

    async def list_messages(self, conversation_id: UUID) -> list[MessageResponse]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return [MessageResponse.model_validate(m) for m in result.scalars().all()]
