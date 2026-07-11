from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.branch_memory.service import BranchMemoryService
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.repository_branches.schemas import (
    BranchMemoryExportResponse,
    BranchMemoryResponse,
    BranchSyncHistoryExportResponse,
    BranchSyncRecordResponse,
    BranchSyncRecordSummary,
    RepositoryBranchCreate,
    RepositoryBranchResponse,
    RepositoryBranchUpdate,
)
from app.repository_branches.service import RepositoryBranchService
from app.repository_memory.schemas import (
    RepositoryMemoryExportResponse,
    RepositoryMemoryJsonExportResponse,
    RepositoryMemoryResponse,
)
from app.repository_memory.service import RepositoryMemoryService
from app.repositories.router import get_repository

repository_branches_router = APIRouter(prefix="/repository-branches", tags=["repository-branches"])


def get_repository_branch_service(db: AsyncSession = Depends(get_db)) -> RepositoryBranchService:
    return RepositoryBranchService(db=db)


def get_branch_memory_service(db: AsyncSession = Depends(get_db)) -> BranchMemoryService:
    return BranchMemoryService(db=db)


async def get_repository_branch(
    repository_branch_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> RepositoryBranch:
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

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository branch not found")
    return row[0]


@repository_branches_router.get("/{repository_branch_id}", response_model=RepositoryBranchResponse)
async def get_repository_branch_detail(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryBranchService = Depends(get_repository_branch_service),
) -> RepositoryBranchResponse:
    return await service.get_branch(branch)


@repository_branches_router.patch("/{repository_branch_id}", response_model=RepositoryBranchResponse)
async def rename_repository_branch(
    data: RepositoryBranchUpdate,
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryBranchService = Depends(get_repository_branch_service),
) -> RepositoryBranchResponse:
    return await service.rename_branch(branch, data)


@repository_branches_router.post("/{repository_branch_id}/archive", response_model=RepositoryBranchResponse)
async def archive_repository_branch(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryBranchService = Depends(get_repository_branch_service),
) -> RepositoryBranchResponse:
    return await service.archive_branch(branch)


@repository_branches_router.post("/{repository_branch_id}/restore", response_model=RepositoryBranchResponse)
async def restore_repository_branch(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryBranchService = Depends(get_repository_branch_service),
) -> RepositoryBranchResponse:
    return await service.restore_branch(branch)


@repository_branches_router.delete("/{repository_branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository_branch(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryBranchService = Depends(get_repository_branch_service),
) -> None:
    await service.delete_inactive_branch(branch)


@repository_branches_router.get(
    "/{repository_branch_id}/history",
    response_model=list[BranchSyncRecordSummary],
)
async def list_repository_branch_history(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: BranchMemoryService = Depends(get_branch_memory_service),
) -> list[BranchSyncRecordSummary]:
    return await service.list_history(branch)


@repository_branches_router.get(
    "/{repository_branch_id}/history/export",
    response_model=BranchSyncHistoryExportResponse,
)
async def export_repository_branch_history(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: BranchMemoryService = Depends(get_branch_memory_service),
) -> BranchSyncHistoryExportResponse:
    return await service.export_history(branch)


@repository_branches_router.get("/{repository_branch_id}/memory", response_model=BranchMemoryResponse)
async def get_repository_branch_memory(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: BranchMemoryService = Depends(get_branch_memory_service),
) -> BranchMemoryResponse:
    return await service.get_memory(branch)


@repository_branches_router.get(
    "/{repository_branch_id}/memory/export",
    response_model=BranchMemoryExportResponse,
)
async def export_repository_branch_memory(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: BranchMemoryService = Depends(get_branch_memory_service),
) -> BranchMemoryExportResponse:
    return await service.export_memory(branch)


def get_repository_memory_service(db: AsyncSession = Depends(get_db)) -> RepositoryMemoryService:
    return RepositoryMemoryService(db=db)


@repository_branches_router.get(
    "/{repository_branch_id}/repository-memory",
    response_model=RepositoryMemoryResponse,
)
async def get_repository_memory(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryMemoryService = Depends(get_repository_memory_service),
) -> RepositoryMemoryResponse:
    return await service.get_memory(branch)


@repository_branches_router.get(
    "/{repository_branch_id}/repository-memory/export",
    response_model=RepositoryMemoryExportResponse,
)
async def export_repository_memory_markdown(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryMemoryService = Depends(get_repository_memory_service),
) -> RepositoryMemoryExportResponse:
    return await service.export_markdown(branch)


@repository_branches_router.get(
    "/{repository_branch_id}/repository-memory/json",
    response_model=RepositoryMemoryJsonExportResponse,
)
async def export_repository_memory_json(
    branch: RepositoryBranch = Depends(get_repository_branch),
    service: RepositoryMemoryService = Depends(get_repository_memory_service),
) -> RepositoryMemoryJsonExportResponse:
    return await service.export_json(branch)


def register_repository_branch_routes(repositories_router: APIRouter) -> None:
    @repositories_router.get(
        "/{repository_id}/branches",
        response_model=list[RepositoryBranchResponse],
    )
    async def list_repository_branches(
        repository: Repository = Depends(get_repository),
        include_inactive: bool = Query(default=False),
        service: RepositoryBranchService = Depends(get_repository_branch_service),
    ) -> list[RepositoryBranchResponse]:
        return await service.list_branches(repository, include_inactive=include_inactive)

    @repositories_router.post(
        "/{repository_id}/branches",
        response_model=RepositoryBranchResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_repository_branch(
        data: RepositoryBranchCreate,
        repository: Repository = Depends(get_repository),
        service: RepositoryBranchService = Depends(get_repository_branch_service),
    ) -> RepositoryBranchResponse:
        return await service.create_branch(repository, data)
