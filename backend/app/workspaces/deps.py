from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.deps import get_current_user
from app.demo.activation import bind_workspace_demo_context, reset_demo_context
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


async def get_workspace_membership(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncIterator[WorkspaceMember]:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    token = await bind_workspace_demo_context(db, workspace_id)
    try:
        yield membership
    finally:
        reset_demo_context(token)


def require_workspace_roles(*allowed_roles: WorkspaceRole):
    async def _check(
        membership: WorkspaceMember = Depends(get_workspace_membership),
    ) -> WorkspaceMember:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient workspace permissions",
            )
        return membership

    return _check


async def get_workspace(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(get_workspace_membership),
) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace
