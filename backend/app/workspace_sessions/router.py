from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.repository import Repository
from app.repositories.router import get_repository
from app.workspace_sessions.schemas import WorkspaceSessionCreate, WorkspaceSessionResponse
from app.workspace_sessions.service import WorkspaceSessionService

workspace_sessions_router = APIRouter(prefix="/workspace-sessions", tags=["workspace-sessions"])


def get_workspace_session_service(db: AsyncSession = Depends(get_db)) -> WorkspaceSessionService:
    return WorkspaceSessionService(db=db)


async def get_workspace_session(
    session_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> DeveloperWorkspaceSession:
    result = await db.execute(
        select(DeveloperWorkspaceSession).where(
            DeveloperWorkspaceSession.id == session_id,
            DeveloperWorkspaceSession.workspace_id == ctx.workspace_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace session not found",
        )
    return session


@workspace_sessions_router.post(
    "",
    response_model=WorkspaceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_session(
    data: WorkspaceSessionCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: WorkspaceSessionService = Depends(get_workspace_session_service),
) -> WorkspaceSessionResponse:
    return await service.create_session(ctx, data)


@workspace_sessions_router.post(
    "/mark-idle",
    response_model=list[WorkspaceSessionResponse],
)
async def mark_idle_workspace_sessions(
    idle_after_seconds: int = Query(default=5 * 60, ge=1),
    disconnected_after_seconds: int = Query(default=15 * 60, ge=1),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: WorkspaceSessionService = Depends(get_workspace_session_service),
) -> list[WorkspaceSessionResponse]:
    """Transition stale sessions to idle/disconnected. Used by tests and future jobs."""
    return await service.mark_idle_sessions(
        workspace_id=ctx.workspace_id,
        idle_after_seconds=idle_after_seconds,
        disconnected_after_seconds=disconnected_after_seconds,
    )


@workspace_sessions_router.get("/{session_id}", response_model=WorkspaceSessionResponse)
async def get_workspace_session_detail(
    session: DeveloperWorkspaceSession = Depends(get_workspace_session),
    service: WorkspaceSessionService = Depends(get_workspace_session_service),
) -> WorkspaceSessionResponse:
    return await service.get_session(session)


@workspace_sessions_router.post(
    "/{session_id}/heartbeat",
    response_model=WorkspaceSessionResponse,
)
async def heartbeat_workspace_session(
    session: DeveloperWorkspaceSession = Depends(get_workspace_session),
    service: WorkspaceSessionService = Depends(get_workspace_session_service),
) -> WorkspaceSessionResponse:
    return await service.heartbeat(session)


@workspace_sessions_router.post(
    "/{session_id}/close",
    response_model=WorkspaceSessionResponse,
)
async def close_workspace_session(
    session: DeveloperWorkspaceSession = Depends(get_workspace_session),
    service: WorkspaceSessionService = Depends(get_workspace_session_service),
) -> WorkspaceSessionResponse:
    return await service.close_session(session)


def register_repository_workspace_session_routes(repositories_router: APIRouter) -> None:
    @repositories_router.get(
        "/{repository_id}/workspace-sessions",
        response_model=list[WorkspaceSessionResponse],
    )
    async def list_repository_workspace_sessions(
        repository: Repository = Depends(get_repository),
        service: WorkspaceSessionService = Depends(get_workspace_session_service),
    ) -> list[WorkspaceSessionResponse]:
        return await service.list_active_sessions(repository)
