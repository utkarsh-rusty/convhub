from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.sync.schemas import SyncPullResponse, SyncPushRequest, SyncPushResponse, SyncStatusResponse
from app.sync.service import SyncService

sync_router = APIRouter(prefix="/sync", tags=["sync"])


def get_sync_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    return SyncService(db=db)


async def get_sync_repository_branch(
    repository_branch_id: UUID = Query(...),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> tuple[RepositoryBranch, Repository]:
    result = await db.execute(
        select(RepositoryBranch, Repository)
        .join(Repository, Repository.id == RepositoryBranch.repository_id)
        .where(
            RepositoryBranch.id == repository_branch_id,
            Repository.workspace_id == ctx.workspace_id,
        )
    )
    row = result.first()
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository branch not found",
        )
    return row[0], row[1]


@sync_router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    branch_and_repository: tuple[RepositoryBranch, Repository] = Depends(get_sync_repository_branch),
    service: SyncService = Depends(get_sync_service),
) -> SyncStatusResponse:
    branch, repository = branch_and_repository
    return await service.get_status(branch, repository)


@sync_router.get("/pull", response_model=SyncPullResponse)
async def get_sync_pull(
    branch_and_repository: tuple[RepositoryBranch, Repository] = Depends(get_sync_repository_branch),
    service: SyncService = Depends(get_sync_service),
) -> SyncPullResponse:
    branch, repository = branch_and_repository
    return await service.get_pull(branch, repository)


@sync_router.post("/push", response_model=SyncPushResponse, status_code=status.HTTP_200_OK)
async def register_sync_push(
    data: SyncPushRequest,
    branch_and_repository: tuple[RepositoryBranch, Repository] = Depends(get_sync_repository_branch),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: SyncService = Depends(get_sync_service),
) -> SyncPushResponse:
    branch, repository = branch_and_repository
    return await service.register_push(
        branch,
        repository,
        user_id=ctx.user.id,
        data=data,
    )
