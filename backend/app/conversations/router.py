from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_conversation, get_workspace_context
from app.conversations.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.conversations.service import ConversationService
from app.models.conversation import Conversation

conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(db: AsyncSession = Depends(get_db)) -> ConversationService:
    return ConversationService(db=db)


@conversations_router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: ConversationCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.create_conversation(ctx, data)


@conversations_router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    return await service.list_conversations(ctx.workspace_id)


@conversations_router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_detail(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.get_conversation(conversation)


@conversations_router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    data: ConversationUpdate,
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.update_conversation(conversation, data)


@conversations_router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    await service.delete_conversation(conversation)


@conversations_router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.archive_conversation(conversation)


@conversations_router.post("/{conversation_id}/restore", response_model=ConversationResponse)
async def restore_conversation(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.restore_conversation(conversation)


@conversations_router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    data: MessageCreate,
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> MessageResponse:
    return await service.create_message(conversation, ctx.user, data)


@conversations_router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    _: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> list[MessageResponse]:
    return await service.list_messages(conversation_id)
