from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.enums import DeveloperWorkspaceSessionStatus
from app.workspace_client.service import WorkspaceClientService
from app.workspace_sessions.service import ACTIVE_STATUSES


def get_workspace_client_service(db: AsyncSession = Depends(get_db)) -> WorkspaceClientService:
    return WorkspaceClientService(db=db)


async def get_active_client_session(
    workspace_session_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> DeveloperWorkspaceSession:
    result = await db.execute(
        select(DeveloperWorkspaceSession).where(
            DeveloperWorkspaceSession.id == workspace_session_id,
            DeveloperWorkspaceSession.workspace_id == ctx.workspace_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace session not found",
        )
    if session.status == DeveloperWorkspaceSessionStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace session is closed",
        )
    if session.status not in ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace session is not active",
        )
    return session
