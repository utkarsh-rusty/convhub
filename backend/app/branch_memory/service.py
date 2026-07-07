from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch_memory import BranchMemory
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.enums import BranchMemorySyncStatus
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.repository_branches.schemas import (
    BranchMemoryExportResponse,
    BranchMemoryResponse,
    BranchMemorySummary,
)


class BranchMemoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_for_branch(self, repository_branch: RepositoryBranch) -> BranchMemory:
        existing = await self.db.execute(
            select(BranchMemory).where(
                BranchMemory.repository_branch_id == repository_branch.id
            )
        )
        memory = existing.scalar_one_or_none()
        if memory is not None:
            return memory

        memory = BranchMemory(
            repository_branch_id=repository_branch.id,
            memory_version=1,
            sync_status=BranchMemorySyncStatus.NOT_SYNCED,
        )
        self.db.add(memory)
        await self.db.flush()
        return memory

    async def get_memory(self, repository_branch: RepositoryBranch) -> BranchMemoryResponse:
        memory = await self._load_memory(repository_branch.id)
        return await self._to_response(memory, repository_branch)

    async def export_memory(self, repository_branch: RepositoryBranch) -> BranchMemoryExportResponse:
        memory = await self._load_memory(repository_branch.id)
        response = await self._to_response(memory, repository_branch)
        return BranchMemoryExportResponse(
            filename="branch-memory.json",
            content={
                "repository_id": str(repository_branch.repository_id),
                "repository_branch_id": str(repository_branch.id),
                "repository_branch_name": repository_branch.name,
                "memory_version": response.memory_version,
                "sync_status": response.sync_status.value,
                "current_conversation_id": (
                    str(response.current_conversation_id)
                    if response.current_conversation_id is not None
                    else None
                ),
                "current_convhub_branch_id": (
                    str(response.current_convhub_branch_id)
                    if response.current_convhub_branch_id is not None
                    else None
                ),
                "current_commit_id": (
                    str(response.current_commit_id)
                    if response.current_commit_id is not None
                    else None
                ),
                "current_context_package_id": (
                    str(response.current_context_package_id)
                    if response.current_context_package_id is not None
                    else None
                ),
                "working_user_id": (
                    str(response.working_user_id)
                    if response.working_user_id is not None
                    else None
                ),
                "last_push_at": (
                    response.last_push_at.isoformat() if response.last_push_at is not None else None
                ),
                "last_pull_at": (
                    response.last_pull_at.isoformat() if response.last_pull_at is not None else None
                ),
                "updated_at": response.updated_at.isoformat(),
            },
        )

    async def sync_for_conversation(
        self,
        conversation: Conversation,
        *,
        working_user_id: UUID | None = None,
        convhub_branch_id: UUID | None = None,
        commit_id: UUID | None = None,
        context_package_id: UUID | None = None,
    ) -> None:
        root = await self._resolve_root_conversation(conversation)
        repository_id = root.repository_id or conversation.repository_id
        if repository_id is None:
            return

        repository_branch = await self._resolve_default_branch(repository_id)
        memory = await self._load_or_create_memory(repository_branch.id)

        memory.current_conversation_id = root.id
        if convhub_branch_id is not None:
            memory.current_convhub_branch_id = convhub_branch_id
        elif conversation.parent_conversation_id is not None:
            memory.current_convhub_branch_id = conversation.id

        if commit_id is not None:
            memory.current_commit_id = commit_id
        if context_package_id is not None:
            memory.current_context_package_id = context_package_id
        if working_user_id is not None:
            memory.working_user_id = working_user_id

        memory.memory_version += 1
        memory.sync_status = BranchMemorySyncStatus.NOT_SYNCED
        await self.db.commit()

    async def detach_for_conversation(
        self,
        conversation: Conversation,
        *,
        repository_id: UUID,
    ) -> None:
        root = await self._resolve_root_conversation(conversation)
        result = await self.db.execute(
            select(BranchMemory)
            .join(RepositoryBranch)
            .where(
                RepositoryBranch.repository_id == repository_id,
                BranchMemory.current_conversation_id == root.id,
            )
        )
        memories = list(result.scalars().all())
        if not memories:
            return

        for memory in memories:
            memory.current_conversation_id = None
            memory.current_convhub_branch_id = None
            memory.current_commit_id = None
            memory.current_context_package_id = None
            memory.working_user_id = None
            memory.memory_version += 1
            memory.sync_status = BranchMemorySyncStatus.NOT_SYNCED
        await self.db.commit()

    async def sync_for_restore(
        self,
        *,
        source_conversation_id: UUID,
        restored_conversation: Conversation,
        package_id: UUID,
        commit_id: UUID | None,
        working_user_id: UUID,
    ) -> None:
        source_result = await self.db.execute(
            select(Conversation).where(Conversation.id == source_conversation_id)
        )
        source = source_result.scalar_one_or_none()
        if source is None:
            return

        root = await self._resolve_root_conversation(source)
        repository_id = root.repository_id
        if repository_id is None:
            return

        repository_branch = await self._resolve_default_branch(repository_id)
        memory = await self._load_or_create_memory(repository_branch.id)
        memory.current_conversation_id = restored_conversation.id
        memory.current_convhub_branch_id = None
        memory.current_context_package_id = package_id
        if commit_id is not None:
            memory.current_commit_id = commit_id
        memory.working_user_id = working_user_id
        memory.memory_version += 1
        memory.sync_status = BranchMemorySyncStatus.NOT_SYNCED
        await self.db.commit()

    async def _load_memory(self, repository_branch_id: UUID) -> BranchMemory:
        result = await self.db.execute(
            select(BranchMemory).where(BranchMemory.repository_branch_id == repository_branch_id)
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch memory not found",
            )
        return memory

    async def _load_or_create_memory(self, repository_branch_id: UUID) -> BranchMemory:
        result = await self.db.execute(
            select(BranchMemory).where(BranchMemory.repository_branch_id == repository_branch_id)
        )
        memory = result.scalar_one_or_none()
        if memory is not None:
            return memory
        branch_result = await self.db.execute(
            select(RepositoryBranch).where(RepositoryBranch.id == repository_branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository branch not found",
            )
        return await self.create_for_branch(branch)

    async def _resolve_default_branch(self, repository_id: UUID) -> RepositoryBranch:
        result = await self.db.execute(
            select(RepositoryBranch)
            .where(
                RepositoryBranch.repository_id == repository_id,
                RepositoryBranch.is_active.is_(True),
            )
            .order_by(RepositoryBranch.is_default.desc(), RepositoryBranch.created_at.asc())
        )
        branch = result.scalars().first()
        if branch is not None:
            return branch

        repository_result = await self.db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = repository_result.scalar_one_or_none()
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        branch = RepositoryBranch(
            repository_id=repository_id,
            name=repository.default_branch.strip() or "main",
            is_default=True,
            is_active=True,
        )
        self.db.add(branch)
        await self.db.flush()
        await self.create_for_branch(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def _resolve_root_conversation(self, conversation: Conversation) -> Conversation:
        current = conversation
        seen: set[UUID] = set()
        while current.parent_conversation_id is not None and current.id not in seen:
            seen.add(current.id)
            parent_result = await self.db.execute(
                select(Conversation).where(Conversation.id == current.parent_conversation_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None:
                break
            current = parent
        return current

    async def _to_response(
        self,
        memory: BranchMemory,
        repository_branch: RepositoryBranch,
    ) -> BranchMemoryResponse:
        conversation_title = None
        convhub_branch_name = None
        commit_hash = None
        package_version = None
        working_user_name = None

        if memory.current_conversation is not None:
            conversation_title = memory.current_conversation.title
        if memory.current_convhub_branch is not None:
            convhub_branch_name = (
                memory.current_convhub_branch.branch_name
                or memory.current_convhub_branch.title
            )
        if memory.current_commit is not None:
            commit_hash = memory.current_commit.commit_hash
        elif memory.current_commit_id is not None:
            commit_result = await self.db.execute(
                select(ConversationCommit.commit_hash).where(
                    ConversationCommit.id == memory.current_commit_id
                )
            )
            commit_hash = commit_result.scalar_one_or_none()
        if memory.current_context_package is not None:
            package_version = memory.current_context_package.version
        elif memory.current_context_package_id is not None:
            package_result = await self.db.execute(
                select(ContextPackage.version).where(
                    ContextPackage.id == memory.current_context_package_id
                )
            )
            package_version = package_result.scalar_one_or_none()
        if memory.working_user is not None:
            working_user_name = memory.working_user.name

        return BranchMemoryResponse(
            id=memory.id,
            repository_branch_id=memory.repository_branch_id,
            repository_id=repository_branch.repository_id,
            repository_branch_name=repository_branch.name,
            current_conversation_id=memory.current_conversation_id,
            current_convhub_branch_id=memory.current_convhub_branch_id,
            current_commit_id=memory.current_commit_id,
            current_context_package_id=memory.current_context_package_id,
            working_user_id=memory.working_user_id,
            working_user_name=working_user_name,
            memory_version=memory.memory_version,
            sync_status=memory.sync_status,
            last_push_at=memory.last_push_at,
            last_pull_at=memory.last_pull_at,
            current_conversation_title=conversation_title,
            current_convhub_branch_name=convhub_branch_name,
            current_commit_hash=commit_hash,
            current_context_package_version=package_version,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    @staticmethod
    def memory_summary(
        memory: BranchMemory | None,
        repository_branch: RepositoryBranch,
    ) -> BranchMemorySummary | None:
        if memory is None:
            return None

        conversation_title = (
            memory.current_conversation.title if memory.current_conversation is not None else None
        )
        convhub_branch_name = None
        if memory.current_convhub_branch is not None:
            convhub_branch_name = (
                memory.current_convhub_branch.branch_name
                or memory.current_convhub_branch.title
            )
        commit_hash = (
            memory.current_commit.commit_hash if memory.current_commit is not None else None
        )
        package_version = (
            memory.current_context_package.version
            if memory.current_context_package is not None
            else None
        )
        working_user_name = (
            memory.working_user.name if memory.working_user is not None else None
        )

        return BranchMemorySummary(
            id=memory.id,
            repository_branch_id=memory.repository_branch_id,
            current_conversation_id=memory.current_conversation_id,
            current_convhub_branch_id=memory.current_convhub_branch_id,
            current_commit_id=memory.current_commit_id,
            current_context_package_id=memory.current_context_package_id,
            working_user_id=memory.working_user_id,
            working_user_name=working_user_name,
            memory_version=memory.memory_version,
            sync_status=memory.sync_status,
            last_push_at=memory.last_push_at,
            last_pull_at=memory.last_pull_at,
            current_conversation_title=conversation_title,
            current_convhub_branch_name=convhub_branch_name,
            current_commit_hash=commit_hash,
            current_context_package_version=package_version,
        )
