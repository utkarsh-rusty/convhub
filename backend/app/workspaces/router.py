from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.deps import get_current_user
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.workspaces.deps import (
    get_workspace,
    get_workspace_membership,
    require_workspace_roles,
)
from app.workspaces.schemas import (
    AcceptInvitationResponse,
    InvitationCreate,
    InvitationPreviewResponse,
    InvitationResponse,
    PendingInvitationResponse,
    WorkspaceCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.workspaces.service import WorkspaceService

workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


def get_workspace_service(db: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(db=db)


@workspaces_router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    return await service.create_workspace(current_user, data)


@workspaces_router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[WorkspaceResponse]:
    return await service.list_workspaces(current_user)


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_detail(
    workspace: Workspace = Depends(get_workspace),
    membership: WorkspaceMember = Depends(get_workspace_membership),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    return await service.get_workspace(workspace, membership)


@workspaces_router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    data: WorkspaceUpdate,
    workspace: Workspace = Depends(get_workspace),
    membership: WorkspaceMember = Depends(
        require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    ),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    return await service.update_workspace(workspace, membership, data)


@workspaces_router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace: Workspace = Depends(get_workspace),
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.delete_workspace(workspace)


@workspaces_router.post(
    "/{workspace_id}/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    data: InvitationCreate,
    workspace: Workspace = Depends(get_workspace),
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> InvitationResponse:
    return await service.create_invitation(workspace, current_user, data)


@workspaces_router.get(
    "/{workspace_id}/invitations",
    response_model=list[PendingInvitationResponse],
)
async def list_pending_invitations(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[PendingInvitationResponse]:
    return await service.list_pending_invitations(workspace_id)


@workspaces_router.post(
    "/{workspace_id}/invitations/{invitation_id}/link",
    response_model=InvitationResponse,
)
async def refresh_invitation_link(
    workspace_id: UUID,
    invitation_id: UUID,
    _: WorkspaceMember = Depends(require_workspace_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> InvitationResponse:
    return await service.refresh_invitation_link(workspace_id, invitation_id)


@workspaces_router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_members(
    workspace_id: UUID,
    _: WorkspaceMember = Depends(get_workspace_membership),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[WorkspaceMemberResponse]:
    return await service.list_members(workspace_id)


@invitations_router.get("/{token}", response_model=InvitationPreviewResponse)
async def preview_invitation(
    token: str,
    service: WorkspaceService = Depends(get_workspace_service),
) -> InvitationPreviewResponse:
    return await service.preview_invitation(token)


@invitations_router.post("/{token}/accept", response_model=AcceptInvitationResponse)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> AcceptInvitationResponse:
    return await service.accept_invitation(current_user, token)
