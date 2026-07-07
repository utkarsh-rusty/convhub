from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import ConversationResponse
from app.conversations.service import ConversationService
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.message import Message
from app.models.project import Project
from app.models.repository import Repository
from app.repositories.schemas import (
    RepositoryAttachRequest,
    RepositoryConversationSummary,
    RepositoryCreate,
    RepositoryResponse,
    RepositorySummary,
    RepositoryUpdate,
)


class RepositoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_repository(
        self,
        ctx: WorkspaceContext,
        data: RepositoryCreate,
    ) -> RepositoryResponse:
        await self._load_project(data.project_id, ctx.workspace_id)
        repository = Repository(
            workspace_id=ctx.workspace_id,
            project_id=data.project_id,
            name=data.name.strip(),
            provider=data.provider,
            owner=data.owner.strip(),
            repository_name=data.repository_name.strip(),
            remote_url=data.remote_url.strip(),
            default_branch=data.default_branch.strip() or "main",
            visibility=data.visibility,
            is_active=data.is_active,
            created_by_id=ctx.user.id,
        )
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)
        return await self._to_response(repository, include_details=False)

    async def list_repositories(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[RepositoryResponse]:
        query = select(Repository).where(Repository.workspace_id == workspace_id)
        if project_id is not None:
            query = query.where(Repository.project_id == project_id)
        if not include_archived:
            query = query.where(Repository.archived_at.is_(None))
        query = query.order_by(Repository.name.asc(), Repository.created_at.asc())
        result = await self.db.execute(query)
        repositories = list(result.scalars().all())
        return [await self._to_response(item, include_details=False) for item in repositories]

    async def get_repository(
        self,
        repository: Repository,
        *,
        include_details: bool = True,
    ) -> RepositoryResponse:
        return await self._to_response(repository, include_details=include_details)

    async def update_repository(
        self,
        repository: Repository,
        data: RepositoryUpdate,
    ) -> RepositoryResponse:
        if data.name is not None:
            repository.name = data.name.strip()
        if data.provider is not None:
            repository.provider = data.provider
        if data.owner is not None:
            repository.owner = data.owner.strip()
        if data.repository_name is not None:
            repository.repository_name = data.repository_name.strip()
        if data.remote_url is not None:
            repository.remote_url = data.remote_url.strip()
        if data.default_branch is not None:
            repository.default_branch = data.default_branch.strip() or "main"
        if data.visibility is not None:
            repository.visibility = data.visibility
        if data.is_active is not None:
            repository.is_active = data.is_active
        await self.db.commit()
        await self.db.refresh(repository)
        return await self._to_response(repository, include_details=False)

    async def archive_repository(self, repository: Repository) -> RepositoryResponse:
        if repository.archived_at is None:
            repository.archived_at = datetime.now(UTC)
            repository.is_active = False
            await self.db.commit()
            await self.db.refresh(repository)
        return await self._to_response(repository, include_details=False)

    async def restore_repository(self, repository: Repository) -> RepositoryResponse:
        if repository.archived_at is not None:
            repository.archived_at = None
            repository.is_active = True
            await self.db.commit()
            await self.db.refresh(repository)
        return await self._to_response(repository, include_details=False)

    async def delete_repository(self, repository: Repository) -> None:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.repository_id == repository.id)
        )
        if int(count_result.scalar_one()) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a repository that is connected to conversations",
            )
        await self.db.delete(repository)
        await self.db.commit()

    async def list_repository_conversations(
        self,
        repository: Repository,
        viewer_user_id: UUID,
    ) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.repository_id == repository.id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        conversations = list(result.scalars().all())
        return await ConversationService(self.db)._build_conversation_responses(
            conversations,
            viewer_user_id=viewer_user_id,
        )

    async def attach_to_conversation(
        self,
        conversation: Conversation,
        data: RepositoryAttachRequest,
        ctx: WorkspaceContext,
    ) -> ConversationResponse:
        from app.repositories.schemas import RepositoryCreate

        if not conversation.coding_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coding workspace must be enabled before connecting a repository",
            )

        if data.create_repository is not None:
            created = await self.create_repository(
                ctx,
                RepositoryCreate(
                    project_id=conversation.project_id,
                    **data.create_repository.model_dump(),
                ),
            )
            repository_id = created.id
        else:
            repository = await self._load_repository(data.repository_id, ctx.workspace_id)
            if repository.project_id != conversation.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Repository must belong to the same project as the conversation",
                )
            if repository.archived_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot attach an archived repository",
                )
            repository_id = repository.id

        previous_repository_id = conversation.repository_id
        conversation.repository_id = repository_id
        await self.db.commit()
        await self.db.refresh(conversation)

        from app.branch_memory.service import BranchMemoryService

        memory_service = BranchMemoryService(self.db)
        if previous_repository_id is not None and previous_repository_id != repository_id:
            await memory_service.detach_for_conversation(
                conversation,
                repository_id=previous_repository_id,
            )
        await memory_service.sync_for_conversation(
            conversation,
            working_user_id=ctx.user.id,
        )
        return await ConversationService(self.db).get_conversation(
            conversation,
            viewer_user_id=ctx.user.id,
        )

    async def detach_from_conversation(
        self,
        conversation: Conversation,
        ctx: WorkspaceContext,
    ) -> ConversationResponse:
        if not conversation.coding_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coding workspace must be enabled before detaching a repository",
            )
        if conversation.repository_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No repository is attached to this conversation",
            )

        repository_id = conversation.repository_id
        conversation.repository_id = None
        await self.db.commit()
        await self.db.refresh(conversation)

        from app.branch_memory.service import BranchMemoryService

        await BranchMemoryService(self.db).detach_for_conversation(
            conversation,
            repository_id=repository_id,
        )
        return await ConversationService(self.db).get_conversation(
            conversation,
            viewer_user_id=ctx.user.id,
        )

    async def resolve_repository_for_create(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        repository_id: UUID | None,
    ) -> Repository | None:
        if repository_id is None:
            return None
        repository = await self._load_repository(repository_id, workspace_id)
        if repository.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository must belong to the same project as the conversation",
            )
        if repository.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot attach an archived repository",
            )
        return repository

    @staticmethod
    def repository_summary(repository: Repository | None) -> RepositorySummary | None:
        if repository is None:
            return None
        return RepositorySummary(
            id=repository.id,
            name=repository.name,
            provider=repository.provider,
            owner=repository.owner,
            repository_name=repository.repository_name,
            remote_url=repository.remote_url,
            default_branch=repository.default_branch,
            visibility=repository.visibility,
            sync_status="not_synced",
        )

    async def _load_project(self, project_id: UUID, workspace_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def _load_repository(self, repository_id: UUID, workspace_id: UUID) -> Repository:
        result = await self.db.execute(
            select(Repository).where(
                Repository.id == repository_id,
                Repository.workspace_id == workspace_id,
            )
        )
        repository = result.scalar_one_or_none()
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )
        return repository

    async def _to_response(
        self,
        repository: Repository,
        *,
        include_details: bool,
    ) -> RepositoryResponse:
        conversation_count = await self._conversation_count(repository.id)
        created_by_name = (
            repository.created_by.name if repository.created_by is not None else None
        )
        connected: list[RepositoryConversationSummary] = []
        if include_details:
            connected = await self._load_connected_conversations(repository.id)

        return RepositoryResponse(
            id=repository.id,
            workspace_id=repository.workspace_id,
            project_id=repository.project_id,
            name=repository.name,
            provider=repository.provider,
            owner=repository.owner,
            repository_name=repository.repository_name,
            remote_url=repository.remote_url,
            default_branch=repository.default_branch,
            visibility=repository.visibility,
            is_active=repository.is_active,
            created_by_id=repository.created_by_id,
            created_by_name=created_by_name,
            created_at=repository.created_at,
            updated_at=repository.updated_at,
            archived_at=repository.archived_at,
            conversation_count=conversation_count,
            sync_status="not_synced",
            latest_commit=None,
            connected_conversations=connected,
        )

    async def _conversation_count(self, repository_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.repository_id == repository_id,
                Conversation.archived_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def _load_connected_conversations(
        self,
        repository_id: UUID,
        *,
        limit: int = 12,
    ) -> list[RepositoryConversationSummary]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.repository_id == repository_id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
            .limit(limit)
        )
        conversations = list(result.scalars().all())
        if not conversations:
            return []

        conversation_ids = [item.id for item in conversations]
        message_counts = await self.db.execute(
            select(Message.conversation_id, func.count())
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
        )
        message_map = {row[0]: int(row[1]) for row in message_counts.all()}

        commit_counts = await self.db.execute(
            select(ConversationCommit.conversation_id, func.count())
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .group_by(ConversationCommit.conversation_id)
        )
        commit_map = {row[0]: int(row[1]) for row in commit_counts.all()}

        return [
            RepositoryConversationSummary(
                id=conversation.id,
                title=conversation.title,
                branch_name=conversation.branch_name,
                parent_conversation_id=conversation.parent_conversation_id,
                last_activity_at=conversation.last_activity_at,
                message_count=message_map.get(conversation.id, 0),
                commit_count=commit_map.get(conversation.id, 0),
            )
            for conversation in conversations
        ]
