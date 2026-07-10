from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_memory.service import BranchMemoryService
from app.conversations.deps import WorkspaceContext
from app.models.branch_memory import BranchMemory
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.sync.schemas import SyncPushRequest
from app.sync.service import SyncService
from app.workspace_client.schemas import (
    WorkspaceClientConnectRequest,
    WorkspaceClientConnectResponse,
    WorkspaceClientDisconnectResponse,
    WorkspaceClientHeartbeatResponse,
    WorkspaceClientProtocolStatusResponse,
    WorkspaceClientPullResponse,
    WorkspaceClientPushRequest,
    WorkspaceClientPushResponse,
)
from app.workspace_sessions.schemas import WorkspaceSessionCreate
from app.workspace_sessions.service import ACTIVE_STATUSES, WorkspaceSessionService


async def _assert_conversation_access(
    conversation_id: UUID,
    ctx: WorkspaceContext,
    db: AsyncSession,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == ctx.workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    participant = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == ctx.user.id,
        )
    )
    if participant.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this conversation",
        )
    return conversation


async def _assert_repository_access(
    repository_id: UUID,
    ctx: WorkspaceContext,
    db: AsyncSession,
) -> Repository:
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.workspace_id == ctx.workspace_id,
        )
    )
    repository = result.scalar_one_or_none()
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    return repository


async def _assert_repository_branch(
    repository_branch_id: UUID,
    repository_id: UUID,
    db: AsyncSession,
) -> RepositoryBranch:
    result = await db.execute(
        select(RepositoryBranch).where(
            RepositoryBranch.id == repository_branch_id,
            RepositoryBranch.repository_id == repository_id,
        )
    )
    branch = result.scalar_one_or_none()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository branch not found",
        )
    return branch


class WorkspaceClientService:
    """Public plugin protocol layer over SyncService + WorkspaceSessionService."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.session_service = WorkspaceSessionService(db)
        self.sync_service = SyncService(db)
        self.branch_memory_service = BranchMemoryService(db)

    async def connect(
        self,
        ctx: WorkspaceContext,
        data: WorkspaceClientConnectRequest,
    ) -> WorkspaceClientConnectResponse:
        repository = await _assert_repository_access(data.repository_id, ctx, self.db)
        branch = await _assert_repository_branch(
            data.repository_branch_id,
            repository.id,
            self.db,
        )
        await _assert_conversation_access(data.conversation_id, ctx, self.db)

        existing = await self._find_resumable_session(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
            repository_id=repository.id,
            repository_branch_id=branch.id,
            conversation_id=data.conversation_id,
            client_name=data.client_name,
        )

        resumed = False
        if existing is not None:
            session_response = await self.session_service.heartbeat(existing)
            session_id = session_response.id
            session_status = session_response.status
            resumed = True
        else:
            session_response = await self.session_service.create_session(
                ctx,
                WorkspaceSessionCreate(
                    repository_id=repository.id,
                    repository_branch_id=branch.id,
                    conversation_id=data.conversation_id,
                    client_name=data.client_name,
                    client_version=data.client_version,
                    platform=data.platform,
                ),
            )
            session_id = session_response.id
            session_status = session_response.status

        sync_status = await self.sync_service.get_status(branch, repository)
        memory = await self._load_memory(branch.id)

        return WorkspaceClientConnectResponse(
            workspace_session_id=session_id,
            sync_state=sync_status.sync_state,
            current_branch_version=memory.current_sync_version,
            current_memory_version=memory.memory_version,
            resumed=resumed,
            session_status=session_status,
        )

    async def heartbeat(
        self,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceClientHeartbeatResponse:
        response = await self.session_service.heartbeat(session)
        return WorkspaceClientHeartbeatResponse(
            workspace_session_id=response.id,
            status=response.status,
            last_heartbeat_at=response.last_heartbeat_at,
        )

    async def push(
        self,
        ctx: WorkspaceContext,
        session: DeveloperWorkspaceSession,
        data: WorkspaceClientPushRequest,
    ) -> WorkspaceClientPushResponse:
        if session.user_id != ctx.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace session belongs to another developer",
            )

        repository, branch = await self._load_session_repo_branch(session)
        await self.session_service.heartbeat(session)

        push = await self.sync_service.register_push(
            branch,
            repository,
            user_id=ctx.user.id,
            data=SyncPushRequest(
                notes=data.notes or "workspace-client push",
                commit_id=data.latest_commit_id,
                context_package_id=data.latest_context_package_id,
            ),
        )
        return WorkspaceClientPushResponse(
            workspace_session_id=session.id,
            sync_version=push.sync_version,
            sync_state=push.sync_state,
            last_synchronized_at=push.last_synchronized_at,
        )

    async def pull(
        self,
        ctx: WorkspaceContext,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceClientPullResponse:
        repository, branch = await self._load_session_repo_branch(session)
        pull = await self.sync_service.get_pull(branch, repository)
        status_response = await self.sync_service.get_status(branch, repository)
        memory = await self._load_memory(branch.id)

        developer_name = session.user.name if session.user is not None else None

        return WorkspaceClientPullResponse(
            workspace_session_id=session.id,
            branch_memory=pull.branch_memory,
            latest_commit=pull.latest_commit,
            latest_context_package=pull.latest_context_package,
            sync_version=pull.branch_sync_version,
            branch_version=memory.current_sync_version,
            active_developer=developer_name,
            sync_state=status_response.sync_state,
        )

    async def disconnect(
        self,
        ctx: WorkspaceContext,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceClientDisconnectResponse:
        if session.user_id != ctx.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace session belongs to another developer",
            )
        response = await self.session_service.close_session(session)
        return WorkspaceClientDisconnectResponse(
            workspace_session_id=response.id,
            status=response.status,
            closed_at=response.closed_at,
        )

    async def protocol_status(
        self,
        repository: Repository,
    ) -> WorkspaceClientProtocolStatusResponse:
        sessions = await self.session_service.list_active_sessions(repository)
        sync_version = None
        result = await self.db.execute(
            select(RepositoryBranch)
            .where(
                RepositoryBranch.repository_id == repository.id,
                RepositoryBranch.is_active.is_(True),
            )
            .order_by(RepositoryBranch.is_default.desc(), RepositoryBranch.created_at.asc())
        )
        default_branch = result.scalars().first()
        if default_branch is not None:
            memory = await self.db.execute(
                select(BranchMemory).where(
                    BranchMemory.repository_branch_id == default_branch.id
                )
            )
            mem = memory.scalar_one_or_none()
            if mem is not None:
                sync_version = mem.current_sync_version

        return WorkspaceClientProtocolStatusResponse(
            plugin_protocol_ready=True,
            connected_sessions=len(sessions),
            current_sync_version=sync_version,
            repository_id=repository.id,
        )

    async def _find_resumable_session(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        repository_id: UUID,
        repository_branch_id: UUID,
        conversation_id: UUID,
        client_name: str,
    ) -> DeveloperWorkspaceSession | None:
        result = await self.db.execute(
            select(DeveloperWorkspaceSession)
            .where(
                DeveloperWorkspaceSession.workspace_id == workspace_id,
                DeveloperWorkspaceSession.user_id == user_id,
                DeveloperWorkspaceSession.repository_id == repository_id,
                DeveloperWorkspaceSession.repository_branch_id == repository_branch_id,
                DeveloperWorkspaceSession.conversation_id == conversation_id,
                DeveloperWorkspaceSession.client_name == client_name,
                DeveloperWorkspaceSession.status.in_(ACTIVE_STATUSES),
            )
            .order_by(DeveloperWorkspaceSession.last_heartbeat_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_session_repo_branch(
        self,
        session: DeveloperWorkspaceSession,
    ) -> tuple[Repository, RepositoryBranch]:
        repo_result = await self.db.execute(
            select(Repository).where(Repository.id == session.repository_id)
        )
        repository = repo_result.scalar_one_or_none()
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )
        branch_result = await self.db.execute(
            select(RepositoryBranch).where(
                RepositoryBranch.id == session.repository_branch_id
            )
        )
        branch = branch_result.scalar_one_or_none()
        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository branch not found",
            )
        return repository, branch

    async def _load_memory(self, repository_branch_id: UUID) -> BranchMemory:
        result = await self.db.execute(
            select(BranchMemory).where(
                BranchMemory.repository_branch_id == repository_branch_id
            )
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch memory not found",
            )
        return memory
