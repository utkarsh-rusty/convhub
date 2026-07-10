from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.models.conversation import Conversation
from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.enums import DeveloperWorkspaceSessionStatus
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.workspace_sessions.schemas import WorkspaceSessionCreate, WorkspaceSessionResponse

DEFAULT_IDLE_AFTER_SECONDS = 5 * 60
DEFAULT_DISCONNECTED_AFTER_SECONDS = 15 * 60

ACTIVE_STATUSES = (
    DeveloperWorkspaceSessionStatus.ACTIVE,
    DeveloperWorkspaceSessionStatus.IDLE,
    DeveloperWorkspaceSessionStatus.DISCONNECTED,
)


class WorkspaceSessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_session(
        self,
        ctx: WorkspaceContext,
        data: WorkspaceSessionCreate,
    ) -> WorkspaceSessionResponse:
        repository = await self._load_repository(data.repository_id, ctx.workspace_id)
        branch = await self._load_branch(data.repository_branch_id, repository.id)
        conversation = await self._load_conversation(data.conversation_id, ctx.workspace_id)

        if conversation.project_id != repository.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation and repository must belong to the same project",
            )
        if conversation.repository_id is not None and conversation.repository_id != repository.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is attached to a different repository",
            )

        now = datetime.now(UTC)
        session = DeveloperWorkspaceSession(
            workspace_id=ctx.workspace_id,
            project_id=repository.project_id,
            repository_id=repository.id,
            repository_branch_id=branch.id,
            conversation_id=conversation.id,
            user_id=ctx.user.id,
            status=DeveloperWorkspaceSessionStatus.ACTIVE,
            started_at=now,
            last_heartbeat_at=now,
            client_name=data.client_name,
            client_version=data.client_version,
            platform=data.platform,
            working_directory=data.working_directory,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return self._to_response(session)

    async def heartbeat(
        self,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceSessionResponse:
        if session.status == DeveloperWorkspaceSessionStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot heartbeat a closed session",
            )

        now = datetime.now(UTC)
        session.last_heartbeat_at = now
        if session.status in (
            DeveloperWorkspaceSessionStatus.IDLE,
            DeveloperWorkspaceSessionStatus.DISCONNECTED,
        ):
            session.status = DeveloperWorkspaceSessionStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(session)
        return self._to_response(session)

    async def close_session(
        self,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceSessionResponse:
        if session.status == DeveloperWorkspaceSessionStatus.CLOSED:
            return self._to_response(session)

        now = datetime.now(UTC)
        session.status = DeveloperWorkspaceSessionStatus.CLOSED
        session.closed_at = now
        await self.db.commit()
        await self.db.refresh(session)
        return self._to_response(session)

    async def mark_idle_sessions(
        self,
        *,
        workspace_id: UUID | None = None,
        idle_after_seconds: int = DEFAULT_IDLE_AFTER_SECONDS,
        disconnected_after_seconds: int = DEFAULT_DISCONNECTED_AFTER_SECONDS,
    ) -> list[WorkspaceSessionResponse]:
        if disconnected_after_seconds < idle_after_seconds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="disconnected_after_seconds must be >= idle_after_seconds",
            )

        now = datetime.now(UTC)
        idle_cutoff = now - timedelta(seconds=idle_after_seconds)
        disconnected_cutoff = now - timedelta(seconds=disconnected_after_seconds)

        query = select(DeveloperWorkspaceSession).where(
            DeveloperWorkspaceSession.status.in_(
                (
                    DeveloperWorkspaceSessionStatus.ACTIVE,
                    DeveloperWorkspaceSessionStatus.IDLE,
                )
            )
        )
        if workspace_id is not None:
            query = query.where(DeveloperWorkspaceSession.workspace_id == workspace_id)

        result = await self.db.execute(query)
        sessions = list(result.scalars().all())
        updated: list[DeveloperWorkspaceSession] = []

        for session in sessions:
            if session.last_heartbeat_at <= disconnected_cutoff:
                if session.status != DeveloperWorkspaceSessionStatus.DISCONNECTED:
                    session.status = DeveloperWorkspaceSessionStatus.DISCONNECTED
                    updated.append(session)
            elif session.last_heartbeat_at <= idle_cutoff:
                if session.status == DeveloperWorkspaceSessionStatus.ACTIVE:
                    session.status = DeveloperWorkspaceSessionStatus.IDLE
                    updated.append(session)

        if updated:
            await self.db.commit()
            for session in updated:
                await self.db.refresh(session)

        return [self._to_response(session) for session in updated]

    async def list_active_sessions(
        self,
        repository: Repository,
    ) -> list[WorkspaceSessionResponse]:
        result = await self.db.execute(
            select(DeveloperWorkspaceSession)
            .where(
                DeveloperWorkspaceSession.repository_id == repository.id,
                DeveloperWorkspaceSession.status.in_(ACTIVE_STATUSES),
            )
            .order_by(DeveloperWorkspaceSession.started_at.desc())
        )
        sessions = list(result.scalars().all())
        return [self._to_response(session) for session in sessions]

    async def get_session(
        self,
        session: DeveloperWorkspaceSession,
    ) -> WorkspaceSessionResponse:
        return self._to_response(session)

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
        if repository.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create a session for an archived repository",
            )
        return repository

    async def _load_branch(
        self,
        repository_branch_id: UUID,
        repository_id: UUID,
    ) -> RepositoryBranch:
        result = await self.db.execute(
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

    async def _load_conversation(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
    ) -> Conversation:
        result = await self.db.execute(
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

    @staticmethod
    def _to_response(session: DeveloperWorkspaceSession) -> WorkspaceSessionResponse:
        user_name = session.user.name if session.user is not None else None
        branch_name = (
            session.repository_branch.name if session.repository_branch is not None else None
        )
        conversation_title = (
            session.conversation.title if session.conversation is not None else None
        )
        return WorkspaceSessionResponse(
            id=session.id,
            workspace_id=session.workspace_id,
            project_id=session.project_id,
            repository_id=session.repository_id,
            repository_branch_id=session.repository_branch_id,
            conversation_id=session.conversation_id,
            user_id=session.user_id,
            status=session.status,
            started_at=session.started_at,
            last_heartbeat_at=session.last_heartbeat_at,
            closed_at=session.closed_at,
            client_name=session.client_name,
            client_version=session.client_version,
            platform=session.platform,
            working_directory=session.working_directory,
            user_name=user_name,
            repository_branch_name=branch_name,
            conversation_title=conversation_title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
