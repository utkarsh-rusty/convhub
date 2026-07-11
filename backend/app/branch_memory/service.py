from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch_memory import BranchMemory
from app.models.branch_sync_record import BranchSyncRecord
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.enums import BranchMemorySyncStatus, BranchSyncType
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.repository_branches.schemas import (
    BranchMemoryExportResponse,
    BranchMemoryResponse,
    BranchMemorySummary,
    BranchSyncHistoryExportResponse,
    BranchSyncRecordResponse,
    BranchSyncRecordSummary,
)

logger = logging.getLogger(__name__)


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
            memory_version=0,
            current_sync_version=0,
            sync_status=BranchMemorySyncStatus.NOT_SYNCED,
        )
        self.db.add(memory)
        await self.db.flush()
        await self._append_sync_record(
            memory,
            sync_type=BranchSyncType.ATTACH_REPOSITORY,
            notes="Branch memory initialized",
        )
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    async def get_memory(self, repository_branch: RepositoryBranch) -> BranchMemoryResponse:
        memory = await self._load_memory(repository_branch.id)
        return await self._to_response(memory, repository_branch)

    async def export_memory(self, repository_branch: RepositoryBranch) -> BranchMemoryExportResponse:
        memory = await self._load_memory(repository_branch.id)
        response = await self._to_response(memory, repository_branch)
        latest = response.latest_sync_record
        return BranchMemoryExportResponse(
            filename="branch-memory.json",
            content={
                "repository_id": str(repository_branch.repository_id),
                "repository_branch_id": str(repository_branch.id),
                "repository_branch_name": repository_branch.name,
                "memory_version": response.memory_version,
                "sync_status": response.sync_status.value,
                "latest_sync_record_id": (
                    str(response.latest_sync_record_id)
                    if response.latest_sync_record_id is not None
                    else None
                ),
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
                "latest_sync_type": latest.sync_type.value if latest is not None else None,
                "updated_at": response.updated_at.isoformat(),
            },
        )

    async def list_history(
        self,
        repository_branch: RepositoryBranch,
    ) -> list[BranchSyncRecordSummary]:
        memory = await self._load_memory(repository_branch.id)
        result = await self.db.execute(
            select(BranchSyncRecord)
            .where(BranchSyncRecord.branch_memory_id == memory.id)
            .order_by(BranchSyncRecord.sync_version.desc(), BranchSyncRecord.created_at.desc())
        )
        records = list(result.scalars().all())
        return [await self._record_to_summary(record) for record in records]

    async def get_sync_record(
        self,
        record: BranchSyncRecord,
        repository_branch: RepositoryBranch,
    ) -> BranchSyncRecordResponse:
        summary = await self._record_to_summary(record)
        return BranchSyncRecordResponse(
            **summary.model_dump(),
            repository_branch_id=repository_branch.id,
            repository_id=repository_branch.repository_id,
            repository_branch_name=repository_branch.name,
        )

    async def export_history(
        self,
        repository_branch: RepositoryBranch,
    ) -> BranchSyncHistoryExportResponse:
        memory = await self._load_memory(repository_branch.id)
        history = await self.list_history(repository_branch)
        return BranchSyncHistoryExportResponse(
            filename="branch-history.json",
            content={
                "repository_id": str(repository_branch.repository_id),
                "repository_branch_id": str(repository_branch.id),
                "repository_branch_name": repository_branch.name,
                "branch_memory_id": str(memory.id),
                "memory_version": memory.memory_version,
                "sync_status": memory.sync_status.value,
                "latest_sync_record_id": (
                    str(memory.latest_sync_record_id)
                    if memory.latest_sync_record_id is not None
                    else None
                ),
                "records": [
                    {
                        "id": str(item.id),
                        "sync_type": item.sync_type.value,
                        "sync_version": item.sync_version,
                        "user_id": str(item.user_id) if item.user_id is not None else None,
                        "user_name": item.user_name,
                        "conversation_id": (
                            str(item.conversation_id)
                            if item.conversation_id is not None
                            else None
                        ),
                        "conversation_title": item.conversation_title,
                        "convhub_branch_id": (
                            str(item.convhub_branch_id)
                            if item.convhub_branch_id is not None
                            else None
                        ),
                        "convhub_branch_name": item.convhub_branch_name,
                        "commit_id": str(item.commit_id) if item.commit_id is not None else None,
                        "commit_hash": item.commit_hash,
                        "context_package_id": (
                            str(item.context_package_id)
                            if item.context_package_id is not None
                            else None
                        ),
                        "context_package_version": item.context_package_version,
                        "notes": item.notes,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in history
                ],
            },
        )

    async def sync_for_conversation(
        self,
        conversation: Conversation,
        *,
        sync_type: BranchSyncType,
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

        resolved_convhub_branch_id = convhub_branch_id
        if resolved_convhub_branch_id is None and conversation.parent_conversation_id is not None:
            resolved_convhub_branch_id = conversation.id

        await self._append_sync_record(
            memory,
            sync_type=sync_type,
            conversation_id=root.id,
            convhub_branch_id=resolved_convhub_branch_id,
            commit_id=commit_id,
            context_package_id=context_package_id,
            user_id=working_user_id,
        )
        await self.db.commit()
        await self._rebuild_repository_memory(repository_branch.id)

    async def detach_for_conversation(
        self,
        conversation: Conversation,
        *,
        repository_id: UUID,
        working_user_id: UUID | None = None,
    ) -> None:
        root = await self._resolve_root_conversation(conversation)
        result = await self.db.execute(
            select(BranchMemory)
            .join(RepositoryBranch)
            .where(
                RepositoryBranch.repository_id == repository_id,
                BranchMemory.latest_sync_record_id.is_not(None),
            )
        )
        memories = list(result.scalars().all())
        if not memories:
            return

        rebuilt_branch_ids: list[UUID] = []
        for memory in memories:
            latest = memory.latest_sync_record
            if latest is None or latest.conversation_id != root.id:
                continue
            await self._append_sync_record(
                memory,
                sync_type=BranchSyncType.DETACH_REPOSITORY,
                conversation_id=root.id,
                user_id=working_user_id,
                notes="Repository detached from conversation",
            )
            rebuilt_branch_ids.append(memory.repository_branch_id)
        await self.db.commit()
        for branch_id in rebuilt_branch_ids:
            await self._rebuild_repository_memory(branch_id)

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
        await self._append_sync_record(
            memory,
            sync_type=BranchSyncType.RESTORE,
            conversation_id=restored_conversation.id,
            convhub_branch_id=None,
            context_package_id=package_id,
            commit_id=commit_id,
            user_id=working_user_id,
        )
        await self.db.commit()
        await self._rebuild_repository_memory(repository_branch.id)

    async def _append_sync_record(
        self,
        memory: BranchMemory,
        *,
        sync_type: BranchSyncType,
        conversation_id: UUID | None = None,
        convhub_branch_id: UUID | None = None,
        commit_id: UUID | None = None,
        context_package_id: UUID | None = None,
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> BranchSyncRecord:
        if sync_type == BranchSyncType.DETACH_REPOSITORY:
            state_conversation_id = conversation_id
            state_convhub_branch_id = None
            state_commit_id = None
            state_context_package_id = None
            state_user_id = user_id
        else:
            latest = memory.latest_sync_record
            state_conversation_id = conversation_id
            if state_conversation_id is None and latest is not None:
                state_conversation_id = latest.conversation_id
            state_convhub_branch_id = convhub_branch_id
            if state_convhub_branch_id is None and latest is not None:
                state_convhub_branch_id = latest.convhub_branch_id
            state_commit_id = commit_id if commit_id is not None else (
                latest.commit_id if latest is not None else None
            )
            state_context_package_id = context_package_id if context_package_id is not None else (
                latest.context_package_id if latest is not None else None
            )
            state_user_id = user_id if user_id is not None else (
                latest.user_id if latest is not None else None
            )

        memory.memory_version += 1
        memory.current_sync_version += 1
        record = BranchSyncRecord(
            branch_memory_id=memory.id,
            conversation_id=state_conversation_id,
            convhub_branch_id=state_convhub_branch_id,
            commit_id=state_commit_id,
            context_package_id=state_context_package_id,
            user_id=state_user_id,
            sync_type=sync_type,
            sync_version=memory.memory_version,
            notes=notes,
        )
        self.db.add(record)
        await self.db.flush()
        memory.latest_sync_record_id = record.id
        memory.sync_status = BranchMemorySyncStatus.NOT_SYNCED
        if sync_type == BranchSyncType.PLUGIN_PUSH:
            memory.last_sync_at = datetime.now(UTC)
        return record

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

    async def _rebuild_repository_memory(self, repository_branch_id: UUID) -> None:
        from app.repository_memory.service import RepositoryMemoryService

        try:
            await RepositoryMemoryService(self.db).build_repository_memory(
                repository_branch_id,
                commit=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to rebuild repository memory for branch %s",
                repository_branch_id,
            )
            await self.db.rollback()

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
        await self._rebuild_repository_memory(branch.id)
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

    async def _record_to_summary(self, record: BranchSyncRecord) -> BranchSyncRecordSummary:
        conversation_title = None
        convhub_branch_name = None
        commit_hash = None
        package_version = None
        user_name = None

        if record.conversation_id is not None:
            conversation_title = (
                await self.db.execute(
                    select(Conversation.title).where(Conversation.id == record.conversation_id)
                )
            ).scalar_one_or_none()
        if record.convhub_branch_id is not None:
            branch_row = (
                await self.db.execute(
                    select(Conversation.branch_name, Conversation.title).where(
                        Conversation.id == record.convhub_branch_id
                    )
                )
            ).one_or_none()
            if branch_row is not None:
                convhub_branch_name = branch_row.branch_name or branch_row.title
        if record.commit_id is not None:
            commit_hash = (
                await self.db.execute(
                    select(ConversationCommit.commit_hash).where(
                        ConversationCommit.id == record.commit_id
                    )
                )
            ).scalar_one_or_none()
        if record.context_package_id is not None:
            package_version = (
                await self.db.execute(
                    select(ContextPackage.version).where(
                        ContextPackage.id == record.context_package_id
                    )
                )
            ).scalar_one_or_none()
        if record.user_id is not None:
            from app.models.user import User

            user_name = (
                await self.db.execute(select(User.name).where(User.id == record.user_id))
            ).scalar_one_or_none()

        return BranchSyncRecordSummary(
            id=record.id,
            branch_memory_id=record.branch_memory_id,
            conversation_id=record.conversation_id,
            convhub_branch_id=record.convhub_branch_id,
            commit_id=record.commit_id,
            context_package_id=record.context_package_id,
            user_id=record.user_id,
            user_name=user_name,
            sync_type=record.sync_type,
            sync_version=record.sync_version,
            notes=record.notes,
            conversation_title=conversation_title,
            convhub_branch_name=convhub_branch_name,
            commit_hash=commit_hash,
            context_package_version=package_version,
            created_at=record.created_at,
        )

    async def _to_response(
        self,
        memory: BranchMemory,
        repository_branch: RepositoryBranch,
    ) -> BranchMemoryResponse:
        latest_summary = None
        if memory.latest_sync_record is not None:
            latest_summary = await self._record_to_summary(memory.latest_sync_record)
        elif memory.latest_sync_record_id is not None:
            record_result = await self.db.execute(
                select(BranchSyncRecord).where(BranchSyncRecord.id == memory.latest_sync_record_id)
            )
            record = record_result.scalar_one_or_none()
            if record is not None:
                latest_summary = await self._record_to_summary(record)

        detached = (
            latest_summary is not None
            and latest_summary.sync_type == BranchSyncType.DETACH_REPOSITORY
        )

        return BranchMemoryResponse(
            id=memory.id,
            repository_branch_id=memory.repository_branch_id,
            repository_id=repository_branch.repository_id,
            repository_branch_name=repository_branch.name,
            latest_sync_record_id=memory.latest_sync_record_id,
            current_conversation_id=(
                None if detached else latest_summary.conversation_id if latest_summary else None
            ),
            current_convhub_branch_id=(
                None if detached else latest_summary.convhub_branch_id if latest_summary else None
            ),
            current_commit_id=(
                None if detached else latest_summary.commit_id if latest_summary else None
            ),
            current_context_package_id=(
                None
                if detached
                else latest_summary.context_package_id if latest_summary else None
            ),
            working_user_id=(
                None if detached else latest_summary.user_id if latest_summary else None
            ),
            working_user_name=(
                None if detached else latest_summary.user_name if latest_summary else None
            ),
            memory_version=memory.memory_version,
            current_sync_version=memory.current_sync_version,
            last_sync_at=memory.last_sync_at,
            sync_status=memory.sync_status,
            current_conversation_title=(
                None
                if detached
                else latest_summary.conversation_title if latest_summary else None
            ),
            current_convhub_branch_name=(
                None
                if detached
                else latest_summary.convhub_branch_name if latest_summary else None
            ),
            current_commit_hash=(
                None if detached else latest_summary.commit_hash if latest_summary else None
            ),
            current_context_package_version=(
                None
                if detached
                else latest_summary.context_package_version if latest_summary else None
            ),
            latest_sync_record=latest_summary,
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

        latest = memory.latest_sync_record
        latest_summary = None
        if latest is not None:
            # Related objects are noload; summary uses record columns only.
            latest_summary = BranchSyncRecordSummary(
                id=latest.id,
                branch_memory_id=latest.branch_memory_id,
                conversation_id=latest.conversation_id,
                convhub_branch_id=latest.convhub_branch_id,
                commit_id=latest.commit_id,
                context_package_id=latest.context_package_id,
                user_id=latest.user_id,
                user_name=None,
                sync_type=latest.sync_type,
                sync_version=latest.sync_version,
                notes=latest.notes,
                conversation_title=None,
                convhub_branch_name=None,
                commit_hash=None,
                context_package_version=None,
                created_at=latest.created_at,
            )

        detached = latest is not None and latest.sync_type == BranchSyncType.DETACH_REPOSITORY

        return BranchMemorySummary(
            id=memory.id,
            repository_branch_id=memory.repository_branch_id,
            latest_sync_record_id=memory.latest_sync_record_id,
            current_conversation_id=None if detached else (latest.conversation_id if latest else None),
            current_convhub_branch_id=(
                None if detached else (latest.convhub_branch_id if latest else None)
            ),
            current_commit_id=None if detached else (latest.commit_id if latest else None),
            current_context_package_id=(
                None if detached else (latest.context_package_id if latest else None)
            ),
            working_user_id=None if detached else (latest.user_id if latest else None),
            working_user_name=None,
            memory_version=memory.memory_version,
            current_sync_version=memory.current_sync_version,
            last_sync_at=memory.last_sync_at,
            sync_status=memory.sync_status,
            current_conversation_title=None,
            current_convhub_branch_name=None,
            current_commit_hash=None,
            current_context_package_version=None,
            latest_sync_record=latest_summary,
        )
