from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.repository import Repository
from app.repositories.router import get_repository
from app.workspace_client.deps import get_active_client_session, get_workspace_client_service
from app.workspace_client.schemas import (
    WorkspaceClientConnectRequest,
    WorkspaceClientConnectResponse,
    WorkspaceClientDisconnectRequest,
    WorkspaceClientDisconnectResponse,
    WorkspaceClientHeartbeatRequest,
    WorkspaceClientHeartbeatResponse,
    WorkspaceClientProtocolStatusResponse,
    WorkspaceClientPullResponse,
    WorkspaceClientPushRequest,
    WorkspaceClientPushResponse,
)
from app.workspace_client.service import WorkspaceClientService

workspace_client_router = APIRouter(prefix="/workspace-client", tags=["workspace-client"])


@workspace_client_router.post(
    "/connect",
    response_model=WorkspaceClientConnectResponse,
    status_code=status.HTTP_200_OK,
)
async def workspace_client_connect(
    data: WorkspaceClientConnectRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: WorkspaceClientService = Depends(get_workspace_client_service),
) -> WorkspaceClientConnectResponse:
    return await service.connect(ctx, data)


@workspace_client_router.post(
    "/heartbeat",
    response_model=WorkspaceClientHeartbeatResponse,
)
async def workspace_client_heartbeat(
    data: WorkspaceClientHeartbeatRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    service: WorkspaceClientService = Depends(get_workspace_client_service),
) -> WorkspaceClientHeartbeatResponse:
    session = await get_active_client_session(data.workspace_session_id, ctx, db)
    return await service.heartbeat(session)


@workspace_client_router.post(
    "/push",
    response_model=WorkspaceClientPushResponse,
)
async def workspace_client_push(
    data: WorkspaceClientPushRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    service: WorkspaceClientService = Depends(get_workspace_client_service),
) -> WorkspaceClientPushResponse:
    session = await get_active_client_session(data.workspace_session_id, ctx, db)
    return await service.push(ctx, session, data)


@workspace_client_router.get(
    "/pull",
    response_model=WorkspaceClientPullResponse,
)
async def workspace_client_pull(
    workspace_session_id: UUID = Query(...),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    service: WorkspaceClientService = Depends(get_workspace_client_service),
) -> WorkspaceClientPullResponse:
    session = await get_active_client_session(workspace_session_id, ctx, db)
    return await service.pull(ctx, session)


@workspace_client_router.post(
    "/disconnect",
    response_model=WorkspaceClientDisconnectResponse,
)
async def workspace_client_disconnect(
    data: WorkspaceClientDisconnectRequest,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    service: WorkspaceClientService = Depends(get_workspace_client_service),
) -> WorkspaceClientDisconnectResponse:
    session = await get_active_client_session(data.workspace_session_id, ctx, db)
    return await service.disconnect(ctx, session)


def register_repository_workspace_client_routes(repositories_router: APIRouter) -> None:
    @repositories_router.get(
        "/{repository_id}/workspace-client/status",
        response_model=WorkspaceClientProtocolStatusResponse,
    )
    async def get_repository_workspace_client_status(
        repository: Repository = Depends(get_repository),
        service: WorkspaceClientService = Depends(get_workspace_client_service),
    ) -> WorkspaceClientProtocolStatusResponse:
        return await service.protocol_status(repository)
