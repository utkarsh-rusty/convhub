from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.external_ai_sessions.schemas import (
    ExternalAISessionConnectRequest,
    ExternalAISessionDisconnectRequest,
    ExternalAISessionResponse,
    ExternalAISessionUploadRequest,
    TranscriptChunkResponse,
)
from app.models.conversation import Conversation
from app.models.enums import ExternalAISessionStatus
from app.models.external_ai_session import ExternalAISession
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.models.transcript_chunk import TranscriptChunk
from app.models.user import User
from app.transcript_snapshots.service import TranscriptSnapshotService


class ExternalAISessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def connect(
        self,
        ctx: WorkspaceContext,
        data: ExternalAISessionConnectRequest,
    ) -> ExternalAISessionResponse:
        repository = await self._load_repository(data.repository_id, ctx.workspace_id)
        branch = await self._load_branch(data.repository_branch_id, repository.id)
        await self._load_conversation(data.conversation_id, ctx.workspace_id)

        existing = await self._find_resumable_session(
            provider=data.provider,
            repository_id=repository.id,
            repository_branch_id=branch.id,
            workspace_user_id=ctx.user.id,
            machine_identifier=data.machine_identifier.strip(),
        )
        if existing is not None:
            if data.conversation_id is not None and existing.conversation_id != data.conversation_id:
                existing.conversation_id = data.conversation_id
                await self.db.commit()
            await TranscriptSnapshotService(self.db).ensure_snapshot(existing.id)
            return await self._to_response(existing)

        session = ExternalAISession(
            provider=data.provider,
            repository_id=repository.id,
            repository_branch_id=branch.id,
            conversation_id=data.conversation_id,
            workspace_user_id=ctx.user.id,
            machine_identifier=data.machine_identifier.strip(),
            started_at=datetime.now(UTC),
            last_synced_offset=0,
            status=ExternalAISessionStatus.ACTIVE,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        await TranscriptSnapshotService(self.db).rebuild_snapshot(session.id)
        return await self._to_response(session)

    async def upload_chunk(
        self,
        ctx: WorkspaceContext,
        data: ExternalAISessionUploadRequest,
    ) -> TranscriptChunkResponse:
        session = await self._load_session(data.session_id, ctx.workspace_id)
        if session.status != ExternalAISessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload to a closed external AI session",
            )
        if data.end_offset <= data.start_offset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_offset must be greater than start_offset",
            )
        if data.start_offset < session.last_synced_offset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="start_offset is behind last_synced_offset",
            )
        if data.start_offset != session.last_synced_offset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="start_offset must equal last_synced_offset for contiguous append",
            )

        expected_sequence = await self._next_sequence_number(session.id)
        if data.sequence_number != expected_sequence:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"sequence_number must be {expected_sequence}",
            )

        chunk = TranscriptChunk(
            external_ai_session_id=session.id,
            sequence_number=data.sequence_number,
            start_offset=data.start_offset,
            end_offset=data.end_offset,
            raw_content=data.raw_content,
        )
        self.db.add(chunk)
        session.last_synced_offset = data.end_offset
        await self.db.flush()
        await TranscriptSnapshotService(self.db).rebuild_snapshot(session.id, commit=False)
        await self.db.commit()
        await self.db.refresh(chunk)
        return TranscriptChunkResponse.model_validate(chunk)

    async def disconnect(
        self,
        ctx: WorkspaceContext,
        data: ExternalAISessionDisconnectRequest,
    ) -> ExternalAISessionResponse:
        session = await self._load_session(data.session_id, ctx.workspace_id)
        if session.status == ExternalAISessionStatus.CLOSED:
            return await self._to_response(session)

        session.status = ExternalAISessionStatus.CLOSED
        session.ended_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(session)
        return await self._to_response(session)

    async def list_for_repository(
        self,
        repository: Repository,
    ) -> list[ExternalAISessionResponse]:
        result = await self.db.execute(
            select(ExternalAISession)
            .where(ExternalAISession.repository_id == repository.id)
            .order_by(ExternalAISession.started_at.desc(), ExternalAISession.id.desc())
        )
        sessions = list(result.scalars().all())
        return [await self._to_response(session) for session in sessions]

    async def get_session(self, session: ExternalAISession) -> ExternalAISessionResponse:
        return await self._to_response(session)

    async def list_chunks(self, session: ExternalAISession) -> list[TranscriptChunkResponse]:
        result = await self.db.execute(
            select(TranscriptChunk)
            .where(TranscriptChunk.external_ai_session_id == session.id)
            .order_by(TranscriptChunk.sequence_number.asc(), TranscriptChunk.id.asc())
        )
        return [TranscriptChunkResponse.model_validate(chunk) for chunk in result.scalars().all()]

    async def _find_resumable_session(
        self,
        *,
        provider,
        repository_id: UUID,
        repository_branch_id: UUID,
        workspace_user_id: UUID,
        machine_identifier: str,
    ) -> ExternalAISession | None:
        result = await self.db.execute(
            select(ExternalAISession)
            .where(
                ExternalAISession.provider == provider,
                ExternalAISession.repository_id == repository_id,
                ExternalAISession.repository_branch_id == repository_branch_id,
                ExternalAISession.workspace_user_id == workspace_user_id,
                ExternalAISession.machine_identifier == machine_identifier,
                ExternalAISession.status == ExternalAISessionStatus.ACTIVE,
            )
            .order_by(ExternalAISession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _next_sequence_number(self, session_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(TranscriptChunk.sequence_number), 0)).where(
                TranscriptChunk.external_ai_session_id == session_id
            )
        )
        return int(result.scalar_one()) + 1

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
        conversation_id: UUID | None,
        workspace_id: UUID,
    ) -> Conversation | None:
        if conversation_id is None:
            return None
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

    async def _load_session(
        self,
        session_id: UUID,
        workspace_id: UUID,
    ) -> ExternalAISession:
        result = await self.db.execute(
            select(ExternalAISession)
            .join(Repository, Repository.id == ExternalAISession.repository_id)
            .where(
                ExternalAISession.id == session_id,
                Repository.workspace_id == workspace_id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External AI session not found",
            )
        return session

    async def _to_response(self, session: ExternalAISession) -> ExternalAISessionResponse:
        developer_name = (
            await self.db.execute(
                select(User.name).where(User.id == session.workspace_user_id)
            )
        ).scalar_one_or_none()
        branch_name = (
            await self.db.execute(
                select(RepositoryBranch.name).where(
                    RepositoryBranch.id == session.repository_branch_id
                )
            )
        ).scalar_one_or_none()
        chunk_stats = (
            await self.db.execute(
                select(
                    func.count(TranscriptChunk.id),
                    func.max(TranscriptChunk.created_at),
                ).where(TranscriptChunk.external_ai_session_id == session.id)
            )
        ).one()
        chunk_count = int(chunk_stats[0] or 0)
        last_chunk_at = chunk_stats[1]
        last_activity_at = last_chunk_at or session.updated_at or session.started_at

        return ExternalAISessionResponse(
            id=session.id,
            provider=session.provider,
            repository_id=session.repository_id,
            repository_branch_id=session.repository_branch_id,
            conversation_id=session.conversation_id,
            workspace_user_id=session.workspace_user_id,
            machine_identifier=session.machine_identifier,
            started_at=session.started_at,
            ended_at=session.ended_at,
            last_synced_offset=session.last_synced_offset,
            status=session.status,
            chunk_count=chunk_count,
            last_activity_at=last_activity_at,
            developer_name=developer_name,
            repository_branch_name=branch_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
