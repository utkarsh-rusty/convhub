from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.commits import ConversationCommitService
from app.conversations.context_packages import ContextPackageService
from app.conversations.restore import ContextRestoreService
from app.conversations.deps import (
    WorkspaceContext,
    get_conversation,
    get_participant_conversation,
    get_workspace_context,
    require_conversation_owner,
)
from app.conversations.insights import ConversationInsightsService
from app.conversations.schemas import (
    BranchFamilyOverviewResponse,
    BranchManagerResponse,
    BranchTreeResponse,
    CommitCreate,
    CommitDetailResponse,
    CommitGraphResponse,
    CommitListItem,
    CommitSearchResponse,
    ContextPackageExportResponse,
    ContextPackageListItem,
    ContextPackageResponse,
    ContextRestoreRequest,
    ConversationRestoreInfoResponse,
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
    EnableCodingRequest,
    MessageCreate,
    MessageResponse,
)
from app.conversations.service import ConversationService
from app.models.conversation import Conversation
from app.repositories.schemas import RepositoryAttachRequest
from app.repositories.service import RepositoryService

conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])
commits_router = APIRouter(prefix="/commits", tags=["commits"])
context_packages_router = APIRouter(prefix="/context-packages", tags=["context-packages"])


def get_conversation_service(db: AsyncSession = Depends(get_db)) -> ConversationService:
    return ConversationService(db=db)


def get_insights_service(db: AsyncSession = Depends(get_db)) -> ConversationInsightsService:
    return ConversationInsightsService(db=db)


def get_commit_service(db: AsyncSession = Depends(get_db)) -> ConversationCommitService:
    return ConversationCommitService(db=db)


def get_context_package_service(db: AsyncSession = Depends(get_db)) -> ContextPackageService:
    return ContextPackageService(db=db)


def get_restore_service(db: AsyncSession = Depends(get_db)) -> ContextRestoreService:
    return ContextRestoreService(db=db)


def get_repository_service(db: AsyncSession = Depends(get_db)) -> RepositoryService:
    return RepositoryService(db=db)


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


@conversations_router.post(
    "/{conversation_id}/enable-coding",
    response_model=ConversationResponse,
)
async def enable_coding(
    data: EnableCodingRequest,
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.enable_coding(conversation, data, ctx)


@conversations_router.post(
    "/{conversation_id}/disable-coding",
    response_model=ConversationResponse,
)
async def disable_coding(
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.disable_coding(conversation, ctx)


@conversations_router.post(
    "/{conversation_id}/attach-repository",
    response_model=ConversationResponse,
)
async def attach_repository(
    data: RepositoryAttachRequest,
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: RepositoryService = Depends(get_repository_service),
) -> ConversationResponse:
    return await service.attach_to_conversation(conversation, data, ctx)


@conversations_router.post(
    "/{conversation_id}/detach-repository",
    response_model=ConversationResponse,
)
async def detach_repository(
    conversation: Conversation = Depends(require_conversation_owner),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: RepositoryService = Depends(get_repository_service),
) -> ConversationResponse:
    return await service.detach_from_conversation(conversation, ctx)


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
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> BranchTreeResponse:
    return await service.get_branch_tree(conversation, viewer_user_id=ctx.user.id)


@conversations_router.get(
    "/{conversation_id}/branch-manager",
    response_model=BranchManagerResponse,
)
async def get_branch_manager(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> BranchManagerResponse:
    return await service.get_branch_manager(conversation, viewer_user_id=ctx.user.id)


@conversations_router.get(
    "/{conversation_id}/commit-graph",
    response_model=CommitGraphResponse,
)
async def get_commit_graph(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> CommitGraphResponse:
    return await service.get_commit_graph(conversation)


@conversations_router.get(
    "/{conversation_id}/family-overview",
    response_model=BranchFamilyOverviewResponse,
)
async def get_family_overview(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> BranchFamilyOverviewResponse:
    return await service.get_family_overview(conversation)


@conversations_router.get(
    "/{conversation_id}/commits/search",
    response_model=CommitSearchResponse,
)
async def search_commits(
    conversation: Conversation = Depends(get_conversation),
    q: str = Query(default="", max_length=500),
    author: str = Query(default="", max_length=255),
    provider: str = Query(default="", max_length=100),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    service: ConversationInsightsService = Depends(get_insights_service),
) -> CommitSearchResponse:
    return await service.search_commits_advanced(
        conversation,
        query=q,
        author=author,
        provider=provider,
        date_from=date_from,
        date_to=date_to,
    )


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


@conversations_router.post(
    "/{conversation_id}/commit",
    response_model=CommitDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_commit(
    data: CommitCreate,
    conversation: Conversation = Depends(get_participant_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationCommitService = Depends(get_commit_service),
) -> CommitDetailResponse:
    return await service.create_commit(conversation, ctx.user, data)


@conversations_router.get(
    "/{conversation_id}/commits",
    response_model=list[CommitListItem],
)
async def list_conversation_commits(
    conversation: Conversation = Depends(get_conversation),
    service: ConversationCommitService = Depends(get_commit_service),
) -> list[CommitListItem]:
    return await service.list_commits(conversation.id)


@commits_router.get(
    "/{commit_id}/context-package",
    response_model=ContextPackageResponse,
)
async def get_commit_context_package(
    commit_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextPackageService = Depends(get_context_package_service),
) -> ContextPackageResponse:
    return await service.get_by_commit_id(commit_id, ctx.workspace_id)


@commits_router.get("/{commit_hash}", response_model=CommitDetailResponse)
async def get_commit_by_hash(
    commit_hash: str,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ConversationCommitService = Depends(get_commit_service),
) -> CommitDetailResponse:
    detail = await service.get_commit_by_hash(commit_hash)
    if detail.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commit not found",
        )
    return detail


@conversations_router.get(
    "/{conversation_id}/context-packages",
    response_model=list[ContextPackageListItem],
)
async def list_conversation_context_packages(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextPackageService = Depends(get_context_package_service),
) -> list[ContextPackageListItem]:
    return await service.list_for_conversation(conversation.id, ctx.workspace_id)


@context_packages_router.get("/{package_id}", response_model=ContextPackageResponse)
async def get_context_package(
    package_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextPackageService = Depends(get_context_package_service),
) -> ContextPackageResponse:
    return await service.get_by_id(package_id, ctx.workspace_id)


@context_packages_router.get(
    "/{package_id}/export",
    response_model=ContextPackageExportResponse,
)
async def export_context_package(
    package_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextPackageService = Depends(get_context_package_service),
) -> ContextPackageExportResponse:
    return await service.export_by_id(package_id, ctx.workspace_id)


@context_packages_router.post(
    "/{package_id}/restore",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def restore_context_package(
    package_id: UUID,
    data: ContextRestoreRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextRestoreService = Depends(get_restore_service),
) -> ConversationResponse:
    return await service.restore(package_id, ctx, data)


@conversations_router.get(
    "/{conversation_id}/restore-info",
    response_model=ConversationRestoreInfoResponse,
)
async def get_conversation_restore_info(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ContextRestoreService = Depends(get_restore_service),
) -> ConversationRestoreInfoResponse:
    return await service.get_restore_info(conversation, ctx.workspace_id)


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
