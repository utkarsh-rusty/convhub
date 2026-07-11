from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_memory.service import BranchMemoryService
from app.models.branch_memory import BranchMemory
from app.models.branch_sync_record import BranchSyncRecord
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.repository_branches.schemas import (
    RepositoryBranchCreate,
    RepositoryBranchResponse,
    RepositoryBranchUpdate,
)


class RepositoryBranchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_branches(
        self,
        repository: Repository,
        *,
        include_inactive: bool = False,
    ) -> list[RepositoryBranchResponse]:
        query = select(RepositoryBranch).where(RepositoryBranch.repository_id == repository.id)
        if not include_inactive:
            query = query.where(RepositoryBranch.is_active.is_(True))
        query = query.order_by(
            RepositoryBranch.is_default.desc(),
            RepositoryBranch.name.asc(),
            RepositoryBranch.created_at.asc(),
        )
        result = await self.db.execute(query)
        branches = list(result.scalars().all())
        return [self._to_response(branch) for branch in branches]

    async def get_branch(self, branch: RepositoryBranch) -> RepositoryBranchResponse:
        return self._to_response(branch)

    async def create_branch(
        self,
        repository: Repository,
        data: RepositoryBranchCreate,
    ) -> RepositoryBranchResponse:
        name = data.name.strip()
        await self._ensure_unique_name(repository.id, name)

        if data.is_default:
            await self._clear_default_flag(repository.id)

        branch = RepositoryBranch(
            repository_id=repository.id,
            name=name,
            is_default=data.is_default,
            is_active=True,
        )
        self.db.add(branch)
        await self.db.flush()
        await BranchMemoryService(self.db).create_for_branch(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        await BranchMemoryService(self.db)._rebuild_repository_memory(branch.id)
        return self._to_response(branch)

    async def rename_branch(
        self,
        branch: RepositoryBranch,
        data: RepositoryBranchUpdate,
    ) -> RepositoryBranchResponse:
        if data.name is None:
            return self._to_response(branch)

        name = data.name.strip()
        if name != branch.name:
            await self._ensure_unique_name(branch.repository_id, name, exclude_id=branch.id)
            branch.name = name

        await self.db.commit()
        await self.db.refresh(branch)
        return self._to_response(branch)

    async def archive_branch(self, branch: RepositoryBranch) -> RepositoryBranchResponse:
        if not branch.is_active:
            return self._to_response(branch)
        if branch.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot archive the default repository branch",
            )
        branch.is_active = False
        await self.db.commit()
        await self.db.refresh(branch)
        return self._to_response(branch)

    async def restore_branch(self, branch: RepositoryBranch) -> RepositoryBranchResponse:
        if branch.is_active:
            return self._to_response(branch)
        branch.is_active = True
        await self.db.commit()
        await self.db.refresh(branch)
        return self._to_response(branch)

    async def delete_inactive_branch(self, branch: RepositoryBranch) -> None:
        if branch.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only inactive repository branches can be deleted",
            )
        if branch.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the default repository branch",
            )
        memory_id = branch.memory.id if branch.memory is not None else None
        branch_id = branch.id
        await self.db.execute(
            update(BranchMemory)
            .where(BranchMemory.repository_branch_id == branch_id)
            .values(latest_sync_record_id=None)
        )
        if memory_id is not None:
            await self.db.execute(
                delete(BranchSyncRecord).where(BranchSyncRecord.branch_memory_id == memory_id)
            )
            await self.db.execute(delete(BranchMemory).where(BranchMemory.id == memory_id))
        await self.db.execute(delete(RepositoryBranch).where(RepositoryBranch.id == branch_id))
        await self.db.commit()

    async def _ensure_unique_name(
        self,
        repository_id: UUID,
        name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        query = select(RepositoryBranch.id).where(
            RepositoryBranch.repository_id == repository_id,
            RepositoryBranch.name == name,
        )
        if exclude_id is not None:
            query = query.where(RepositoryBranch.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A repository branch with this name already exists",
            )

    async def _clear_default_flag(self, repository_id: UUID) -> None:
        result = await self.db.execute(
            select(RepositoryBranch).where(
                RepositoryBranch.repository_id == repository_id,
                RepositoryBranch.is_default.is_(True),
            )
        )
        for branch in result.scalars().all():
            branch.is_default = False

    async def _ensure_default_branch(self, repository: Repository) -> RepositoryBranch:
        result = await self.db.execute(
            select(RepositoryBranch).where(RepositoryBranch.repository_id == repository.id)
        )
        branches = list(result.scalars().all())
        if branches:
            default = next((branch for branch in branches if branch.is_default), branches[0])
            return default

        branch = RepositoryBranch(
            repository_id=repository.id,
            name=repository.default_branch.strip() or "main",
            is_default=True,
            is_active=True,
        )
        self.db.add(branch)
        await self.db.flush()
        await BranchMemoryService(self.db).create_for_branch(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        await BranchMemoryService(self.db)._rebuild_repository_memory(branch.id)
        return branch

    def _to_response(self, branch: RepositoryBranch) -> RepositoryBranchResponse:
        return RepositoryBranchResponse(
            id=branch.id,
            repository_id=branch.repository_id,
            name=branch.name,
            is_default=branch.is_default,
            is_active=branch.is_active,
            created_at=branch.created_at,
            updated_at=branch.updated_at,
            memory=BranchMemoryService.memory_summary(branch.memory, branch),
        )
