from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.external_ai_sessions.schemas import (
    ExternalAISessionConnectRequest,
    ExternalAISessionDisconnectRequest,
    ExternalAISessionResponse,
    ExternalAISessionUploadRequest,
    TranscriptChunkResponse,
)
from app.external_ai_sessions.service import ExternalAISessionService
from app.models.external_ai_session import ExternalAISession
from app.models.repository import Repository
from app.repositories.router import get_repository
from app.transcript_snapshots.schemas import (
    TranscriptSnapshotExportResponse,
    TranscriptSnapshotResponse,
)
from app.transcript_snapshots.service import TranscriptSnapshotService

external_ai_sessions_router = APIRouter(
    prefix="/external-ai-sessions",
    tags=["external-ai-sessions"],
)


def get_external_ai_session_service(
    db: AsyncSession = Depends(get_db),
) -> ExternalAISessionService:
    return ExternalAISessionService(db=db)


def get_transcript_snapshot_service(
    db: AsyncSession = Depends(get_db),
) -> TranscriptSnapshotService:
    return TranscriptSnapshotService(db=db)


async def get_external_ai_session(
    session_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> ExternalAISession:
    result = await db.execute(
        select(ExternalAISession)
        .join(Repository, Repository.id == ExternalAISession.repository_id)
        .where(
            ExternalAISession.id == session_id,
            Repository.workspace_id == ctx.workspace_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External AI session not found",
        )
    return session


@external_ai_sessions_router.post(
    "/connect",
    response_model=ExternalAISessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_external_ai_session(
    data: ExternalAISessionConnectRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ExternalAISessionService = Depends(get_external_ai_session_service),
) -> ExternalAISessionResponse:
    return await service.connect(ctx, data)


@external_ai_sessions_router.post(
    "/upload",
    response_model=TranscriptChunkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_external_ai_transcript_chunk(
    data: ExternalAISessionUploadRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ExternalAISessionService = Depends(get_external_ai_session_service),
) -> TranscriptChunkResponse:
    return await service.upload_chunk(ctx, data)


@external_ai_sessions_router.post(
    "/disconnect",
    response_model=ExternalAISessionResponse,
)
async def disconnect_external_ai_session(
    data: ExternalAISessionDisconnectRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ExternalAISessionService = Depends(get_external_ai_session_service),
) -> ExternalAISessionResponse:
    return await service.disconnect(ctx, data)


@external_ai_sessions_router.get(
    "/{session_id}",
    response_model=ExternalAISessionResponse,
)
async def get_external_ai_session_detail(
    session: ExternalAISession = Depends(get_external_ai_session),
    service: ExternalAISessionService = Depends(get_external_ai_session_service),
) -> ExternalAISessionResponse:
    return await service.get_session(session)


@external_ai_sessions_router.get(
    "/{session_id}/chunks",
    response_model=list[TranscriptChunkResponse],
)
async def list_external_ai_session_chunks(
    session: ExternalAISession = Depends(get_external_ai_session),
    service: ExternalAISessionService = Depends(get_external_ai_session_service),
) -> list[TranscriptChunkResponse]:
    return await service.list_chunks(session)


@external_ai_sessions_router.get(
    "/{session_id}/snapshot",
    response_model=TranscriptSnapshotResponse,
)
async def get_external_ai_session_snapshot(
    session: ExternalAISession = Depends(get_external_ai_session),
    service: TranscriptSnapshotService = Depends(get_transcript_snapshot_service),
) -> TranscriptSnapshotResponse:
    return await service.get_snapshot(session.id)


@external_ai_sessions_router.get(
    "/{session_id}/snapshot/export",
    response_model=TranscriptSnapshotExportResponse,
)
async def export_external_ai_session_snapshot(
    session: ExternalAISession = Depends(get_external_ai_session),
    service: TranscriptSnapshotService = Depends(get_transcript_snapshot_service),
) -> TranscriptSnapshotExportResponse:
    return await service.export_markdown(session.id)


def register_repository_external_ai_session_routes(repositories_router: APIRouter) -> None:
    @repositories_router.get(
        "/{repository_id}/external-ai-sessions",
        response_model=list[ExternalAISessionResponse],
    )
    async def list_repository_external_ai_sessions(
        repository: Repository = Depends(get_repository),
        service: ExternalAISessionService = Depends(get_external_ai_session_service),
    ) -> list[ExternalAISessionResponse]:
        return await service.list_for_repository(repository)
