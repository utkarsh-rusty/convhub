from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.schemas import ChatSendRequest
from app.ai.service import ChatService
from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.conversations.schemas import MessageResponse
from app.conversations.service import ConversationService
from app.core.config import Settings, get_settings

chat_router = APIRouter(prefix="/chat", tags=["chat"])


def get_ai_gateway(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AIGateway:
    return AIGateway(db=db, settings=settings)


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    gateway: AIGateway = Depends(get_ai_gateway),
) -> ChatService:
    return ChatService(
        db=db,
        conversation_service=ConversationService(db),
        gateway=gateway,
    )


@chat_router.post("/send", response_model=MessageResponse)
async def send_chat_message(
    data: ChatSendRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ChatService = Depends(get_chat_service),
) -> MessageResponse:
    return await service.send(data, ctx)
