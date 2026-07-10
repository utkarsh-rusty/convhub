from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_memory.service import BranchMemoryService
from app.models.branch_memory import BranchMemory
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.enums import BranchMemorySyncStatus, BranchSyncState, BranchSyncType
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.sync.schemas import (
    SyncCommitSummary,
    SyncContextPackageSummary,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncRepositoryBranchSummary,
    SyncRepositorySummary,
    SyncStatusResponse,
)


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.branch_memory_service = BranchMemoryService(db)

    async def get_status(
        self,
        repository_branch: RepositoryBranch,
        repository: Repository,
    ) -> SyncStatusResponse:
        memory = await self._load_memory(repository_branch.id)
        memory_response = await self.branch_memory_service.get_memory(repository_branch)
        latest_record = memory_response.latest_sync_record
        latest_commit, latest_package = await self._resolve_latest_artifacts(memory)
        sync_state = await self._compute_sync_state(
            memory=memory,
            repository=repository,
            branch_commit_id=latest_commit.id if latest_commit is not None else None,
            branch_package_id=latest_package.id if latest_package is not None else None,
        )

        return SyncStatusResponse(
            repository=self._repository_summary(repository),
            repository_branch=self._branch_summary(repository_branch),
            sync_version=memory.current_sync_version,
            sync_state=sync_state,
            latest_commit=latest_commit,
            latest_context_package=latest_package,
            latest_sync_record=latest_record,
            last_synchronized_at=memory.last_sync_at,
        )

    async def get_pull(
        self,
        repository_branch: RepositoryBranch,
        repository: Repository,
    ) -> SyncPullResponse:
        memory = await self._load_memory(repository_branch.id)
        memory_response = await self.branch_memory_service.get_memory(repository_branch)
        latest_commit, latest_package = await self._resolve_latest_artifacts(memory)

        return SyncPullResponse(
            branch_memory=memory_response,
            latest_commit=latest_commit,
            latest_context_package=latest_package,
            latest_sync_record=memory_response.latest_sync_record,
            branch_sync_version=memory.current_sync_version,
        )

    async def register_push(
        self,
        repository_branch: RepositoryBranch,
        repository: Repository,
        *,
        user_id: UUID,
        data: SyncPushRequest,
    ) -> SyncPushResponse:
        memory = await self._load_memory(repository_branch.id)
        latest = memory.latest_sync_record
        if latest is None or latest.sync_type == BranchSyncType.DETACH_REPOSITORY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot push for a detached repository branch",
            )
        if latest.conversation_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active conversation is linked to this repository branch",
            )

        conversation_result = await self.db.execute(
            select(Conversation).where(Conversation.id == latest.conversation_id)
        )
        conversation = conversation_result.scalar_one_or_none()
        if conversation is None or conversation.repository_id != repository.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Linked conversation is not attached to this repository",
            )

        commit = await self._latest_commit_for_conversation(conversation.id)
        package = await self._latest_context_package_for_conversation(conversation.id)

        commit_id = data.commit_id if data.commit_id is not None else (
            commit.id if commit is not None else None
        )
        context_package_id = (
            data.context_package_id
            if data.context_package_id is not None
            else (package.id if package is not None else None)
        )

        if data.commit_id is not None:
            commit_result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == data.commit_id)
            )
            if commit_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Commit not found",
                )
        if data.context_package_id is not None:
            package_result = await self.db.execute(
                select(ContextPackage).where(ContextPackage.id == data.context_package_id)
            )
            if package_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Context package not found",
                )

        convhub_branch_id = latest.convhub_branch_id
        if convhub_branch_id is None and conversation.parent_conversation_id is not None:
            convhub_branch_id = conversation.id

        record = await self.branch_memory_service._append_sync_record(
            memory,
            sync_type=BranchSyncType.PLUGIN_PUSH,
            conversation_id=conversation.id,
            convhub_branch_id=convhub_branch_id,
            commit_id=commit_id,
            context_package_id=context_package_id,
            user_id=user_id,
            notes=data.notes,
        )
        memory.sync_status = BranchMemorySyncStatus.READY
        await self.db.commit()
        await self.db.refresh(memory)

        latest_record = await self.branch_memory_service._record_to_summary(record)
        sync_state = await self._compute_sync_state(
            memory=memory,
            repository=repository,
            branch_commit_id=record.commit_id,
            branch_package_id=record.context_package_id,
        )

        return SyncPushResponse(
            sync_version=memory.current_sync_version,
            sync_state=sync_state,
            latest_sync_record=latest_record,
            last_synchronized_at=memory.last_sync_at or datetime.now(UTC),
        )

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

    async def _resolve_latest_artifacts(
        self,
        memory: BranchMemory,
    ) -> tuple[SyncCommitSummary | None, SyncContextPackageSummary | None]:
        latest = memory.latest_sync_record
        if latest is None or latest.sync_type == BranchSyncType.DETACH_REPOSITORY:
            return None, None

        commit_summary = None
        if latest.commit_id is not None:
            commit_result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == latest.commit_id)
            )
            commit = commit_result.scalar_one_or_none()
            if commit is not None:
                commit_summary = SyncCommitSummary(
                    id=commit.id,
                    commit_hash=commit.commit_hash,
                    title=commit.title,
                    created_at=commit.created_at,
                )

        package_summary = None
        if latest.context_package_id is not None:
            package_result = await self.db.execute(
                select(ContextPackage, ConversationCommit)
                .join(ConversationCommit, ConversationCommit.id == ContextPackage.commit_id)
                .where(ContextPackage.id == latest.context_package_id)
            )
            row = package_result.first()
            if row is not None:
                package, commit = row
                package_summary = SyncContextPackageSummary(
                    id=package.id,
                    commit_id=package.commit_id,
                    commit_hash=commit.commit_hash,
                    version=package.version,
                    generated_at=package.generated_at,
                )

        return commit_summary, package_summary

    async def _compute_sync_state(
        self,
        *,
        memory: BranchMemory,
        repository: Repository,
        branch_commit_id: UUID | None,
        branch_package_id: UUID | None,
    ) -> BranchSyncState:
        latest = memory.latest_sync_record
        if latest is None or latest.sync_type == BranchSyncType.DETACH_REPOSITORY:
            return BranchSyncState.DETACHED

        if memory.sync_status == BranchMemorySyncStatus.CONFLICT:
            return BranchSyncState.CONFLICT

        if latest.conversation_id is None:
            return BranchSyncState.DETACHED

        conversation_result = await self.db.execute(
            select(Conversation).where(Conversation.id == latest.conversation_id)
        )
        conversation = conversation_result.scalar_one_or_none()
        if conversation is None or conversation.repository_id != repository.id:
            return BranchSyncState.DETACHED

        conversation_commit = await self._latest_commit_for_conversation(conversation.id)
        conversation_package = await self._latest_context_package_for_conversation(conversation.id)
        conversation_commit_id = conversation_commit.id if conversation_commit is not None else None
        conversation_package_id = (
            conversation_package.id if conversation_package is not None else None
        )

        if (
            branch_commit_id == conversation_commit_id
            and branch_package_id == conversation_package_id
        ):
            return BranchSyncState.SYNCED

        branch_commit = None
        if branch_commit_id is not None:
            commit_result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == branch_commit_id)
            )
            branch_commit = commit_result.scalar_one_or_none()

        if conversation_commit_id is None and branch_commit_id is not None:
            return BranchSyncState.BEHIND
        if conversation_commit_id is not None and branch_commit_id is None:
            return BranchSyncState.AHEAD

        if conversation_commit is not None and branch_commit is not None:
            if conversation_commit.created_at > branch_commit.created_at:
                return BranchSyncState.AHEAD
            if branch_commit.created_at > conversation_commit.created_at:
                return BranchSyncState.BEHIND
            if conversation_commit.id != branch_commit.id:
                return BranchSyncState.CONFLICT

        if conversation_package_id is not None or branch_package_id is not None:
            branch_package_version = None
            conversation_package_version = None
            if branch_package_id is not None:
                package_result = await self.db.execute(
                    select(ContextPackage.version).where(ContextPackage.id == branch_package_id)
                )
                branch_package_version = package_result.scalar_one_or_none()
            if conversation_package_id is not None:
                package_result = await self.db.execute(
                    select(ContextPackage.version).where(ContextPackage.id == conversation_package_id)
                )
                conversation_package_version = package_result.scalar_one_or_none()

            if (
                conversation_package_version is not None
                and branch_package_version is not None
                and conversation_package_version > branch_package_version
            ):
                return BranchSyncState.AHEAD
            if (
                branch_package_version is not None
                and conversation_package_version is not None
                and branch_package_version > conversation_package_version
            ):
                return BranchSyncState.BEHIND
            if conversation_package_id != branch_package_id:
                return BranchSyncState.CONFLICT

        return BranchSyncState.SYNCED

    async def _latest_commit_for_conversation(
        self,
        conversation_id: UUID,
    ) -> ConversationCommit | None:
        result = await self.db.execute(
            select(ConversationCommit)
            .where(ConversationCommit.conversation_id == conversation_id)
            .order_by(ConversationCommit.created_at.desc(), ConversationCommit.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _latest_context_package_for_conversation(
        self,
        conversation_id: UUID,
    ) -> ContextPackage | None:
        result = await self.db.execute(
            select(ContextPackage)
            .where(ContextPackage.conversation_id == conversation_id)
            .order_by(ContextPackage.generated_at.desc(), ContextPackage.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _repository_summary(repository: Repository) -> SyncRepositorySummary:
        return SyncRepositorySummary(
            id=repository.id,
            name=repository.name,
            provider=repository.provider,
            owner=repository.owner,
            repository_name=repository.repository_name,
            remote_url=repository.remote_url,
            default_branch=repository.default_branch,
            visibility=repository.visibility,
        )

    @staticmethod
    def _branch_summary(repository_branch: RepositoryBranch) -> SyncRepositoryBranchSummary:
        return SyncRepositoryBranchSummary(
            id=repository_branch.id,
            repository_id=repository_branch.repository_id,
            name=repository_branch.name,
            is_default=repository_branch.is_default,
            is_active=repository_branch.is_active,
        )
