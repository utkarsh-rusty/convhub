from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.branch_memory.service import BranchMemoryService
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.branch_memory import BranchMemory
from app.models.branch_sync_record import BranchSyncRecord
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.repository_branches.schemas import BranchSyncRecordResponse

branch_sync_records_router = APIRouter(prefix="/branch-sync-records", tags=["branch-sync-records"])


def get_branch_memory_service(db: AsyncSession = Depends(get_db)) -> BranchMemoryService:
    return BranchMemoryService(db=db)


async def get_branch_sync_record(
    branch_sync_record_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> tuple[BranchSyncRecord, RepositoryBranch]:
    result = await db.execute(
        select(BranchSyncRecord, RepositoryBranch)
        .join(BranchMemory, BranchMemory.id == BranchSyncRecord.branch_memory_id)
        .join(RepositoryBranch, RepositoryBranch.id == BranchMemory.repository_branch_id)
        .join(Repository, Repository.id == RepositoryBranch.repository_id)
        .where(
            BranchSyncRecord.id == branch_sync_record_id,
            Repository.workspace_id == ctx.workspace_id,
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch sync record not found",
        )
    return row[0], row[1]


@branch_sync_records_router.get("/{branch_sync_record_id}", response_model=BranchSyncRecordResponse)
async def get_branch_sync_record_detail(
    record_and_branch: tuple[BranchSyncRecord, RepositoryBranch] = Depends(get_branch_sync_record),
    service: BranchMemoryService = Depends(get_branch_memory_service),
) -> BranchSyncRecordResponse:
    record, branch = record_and_branch
    return await service.get_sync_record(record, branch)
