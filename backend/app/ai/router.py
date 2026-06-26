from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.schemas import ChatSendRequest
from app.ai.service import ChatService
from app.ai_accounts.deps import get_ai_account_service, get_credential_encryption
from app.ai_accounts.service import AIAccountService
from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.conversations.schemas import MessageResponse
from app.conversations.service import ConversationService
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialEncryption
from app.resource_management.budget_service import BudgetService
from app.routing.engine import RoutingEngine

chat_router = APIRouter(prefix="/chat", tags=["chat"])


def get_budget_service(db: AsyncSession = Depends(get_db)) -> BudgetService:
    return BudgetService(db=db)


def get_routing_engine(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    encryption: CredentialEncryption = Depends(get_credential_encryption),
    ai_account_service: AIAccountService = Depends(get_ai_account_service),
    budget_service: BudgetService = Depends(get_budget_service),
) -> RoutingEngine:
    return RoutingEngine(
        db=db,
        settings=settings,
        encryption=encryption,
        ai_account_service=ai_account_service,
        budget_service=budget_service,
    )


def get_ai_gateway(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    encryption: CredentialEncryption = Depends(get_credential_encryption),
    budget_service: BudgetService = Depends(get_budget_service),
    routing_engine: RoutingEngine = Depends(get_routing_engine),
) -> AIGateway:
    ai_account_service = AIAccountService(db=db, settings=settings, encryption=encryption)
    return AIGateway(
        db=db,
        settings=settings,
        ai_account_service=ai_account_service,
        budget_service=budget_service,
        routing_engine=routing_engine,
    )


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
