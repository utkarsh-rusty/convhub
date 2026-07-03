from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import (
    WorkspaceContext,
    get_conversation,
    get_participant_conversation,
    get_workspace_context,
    require_conversation_owner,
)
from app.conversations.insights import ConversationInsightsService
from app.conversations.schemas import (
    BranchTreeResponse,
    ConversationBranchCreate,
    ConversationCompareResponse,
    ConversationCreate,
    ConversationLineageResponse,
    ConversationParticipantCreate,
    ConversationParticipantResponse,
    ConversationResponse,
    ConversationSearchResponse,
    ConversationStatsResponse,
    ConversationTimelineResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.conversations.service import ConversationService
from app.models.conversation import Conversation

conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(db: AsyncSession = Depends(get_db)) -> ConversationService:
    return ConversationService(db=db)


def get_insights_service(db: AsyncSession = Depends(get_db)) -> ConversationInsightsService:
    return ConversationInsightsService(db=db)


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
    return await service.list_conversations(ctx.workspace_id, ctx.user.id)


@conversations_router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_detail(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.get_conversation(conversation, viewer_user_id=ctx.user.id)


@conversations_router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    data: ConversationUpdate,
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.update_conversation(
        conversation,
        data,
        viewer_user_id=ctx.user.id,
    )


@conversations_router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation: Conversation = Depends(require_conversation_owner),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    await service.delete_conversation(conversation)


@conversations_router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.archive_conversation(conversation, viewer_user_id=ctx.user.id)


@conversations_router.post("/{conversation_id}/restore", response_model=ConversationResponse)
async def restore_conversation(
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.restore_conversation(conversation, viewer_user_id=ctx.user.id)


@conversations_router.get(
    "/{conversation_id}/participants",
    response_model=list[ConversationParticipantResponse],
)
async def list_participants(
    conversation_id: UUID,
    _: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationParticipantResponse]:
    return await service.list_participants(conversation_id)


@conversations_router.post(
    "/{conversation_id}/participants",
    response_model=list[ConversationParticipantResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_participants(
    data: ConversationParticipantCreate,
    conversation: Conversation = Depends(require_conversation_owner),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationParticipantResponse]:
    return await service.add_participants(conversation, data)


@conversations_router.delete(
    "/{conversation_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_participant(
    user_id: UUID,
    conversation: Conversation = Depends(require_conversation_owner),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    await service.remove_participant(conversation, user_id)


@conversations_router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    data: MessageCreate,
    conversation: Conversation = Depends(get_participant_conversation),
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


@conversations_router.post(
    "/{conversation_id}/branch",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_branch(
    data: ConversationBranchCreate,
    conversation: Conversation = Depends(get_participant_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.create_branch(conversation, ctx, data)


@conversations_router.get(
    "/{conversation_id}/branches",
    response_model=list[ConversationResponse],
)
async def list_conversation_branches(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    return await service.list_branches(conversation, viewer_user_id=ctx.user.id)


@conversations_router.get(
    "/{conversation_id}/lineage",
    response_model=ConversationLineageResponse,
)
async def get_conversation_lineage(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationLineageResponse:
    return await service.get_lineage(conversation)


@conversations_router.get(
    "/{conversation_id}/branch-tree",
    response_model=BranchTreeResponse,
)
async def get_branch_tree(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> BranchTreeResponse:
    return await service.get_branch_tree(conversation)


@conversations_router.get(
    "/{left_id}/compare/{right_id}",
    response_model=ConversationCompareResponse,
)
async def compare_conversations(
    left_id: UUID,
    right_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> ConversationCompareResponse:
    left = await _load_workspace_conversation(db, left_id, ctx.workspace_id)
    right = await _load_workspace_conversation(db, right_id, ctx.workspace_id)
    return await service.compare(left, right)


@conversations_router.get(
    "/{conversation_id}/timeline",
    response_model=ConversationTimelineResponse,
)
async def get_conversation_timeline(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> ConversationTimelineResponse:
    return await service.get_timeline(conversation)


@conversations_router.get(
    "/{conversation_id}/stats",
    response_model=ConversationStatsResponse,
)
async def get_conversation_stats(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> ConversationStatsResponse:
    return await service.get_stats(conversation)


@conversations_router.get(
    "/{conversation_id}/search",
    response_model=ConversationSearchResponse,
)
async def search_conversation_messages(
    conversation: Conversation = Depends(get_conversation),
    q: str = Query(default="", max_length=500),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> ConversationSearchResponse:
    return await service.search(conversation, q)


async def _load_workspace_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    workspace_id: UUID,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation
