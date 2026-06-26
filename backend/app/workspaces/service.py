from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import WorkspaceRole
from app.models.invitation import Invitation
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_sharing.preference_service import LendingPreferenceService
from app.workspaces.schemas import (
    AcceptInvitationResponse,
    InvitationCreate,
    InvitationResponse,
    WorkspaceCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.workspaces.utils import (
    generate_invitation_token,
    hash_invitation_token,
    invitation_expires_at,
    slugify,
    unique_slug,
)


class WorkspaceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_workspace(self, user: User, data: WorkspaceCreate) -> WorkspaceResponse:
        base_slug = slugify(data.slug or data.name)

        async def slug_exists(candidate: str) -> bool:
            result = await self.db.execute(select(Workspace.id).where(Workspace.slug == candidate))
            return result.scalar_one_or_none() is not None

        slug = await unique_slug(base_slug, slug_exists)

        workspace = Workspace(
            name=data.name,
            slug=slug,
            owner_id=user.id,
        )
        membership = WorkspaceMember(
            workspace=workspace,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
        )
        self.db.add(workspace)
        self.db.add(membership)
        await self.db.flush()
        await BudgetService(self.db).create_workspace_budget_settings(workspace.id)
        await BudgetService(self.db).create_budget(workspace.id, user.id)
        await LendingPreferenceService(self.db).create_preference(workspace.id, user.id)

        try:
            await self.db.commit()
            await self.db.refresh(workspace)
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace slug already exists",
            ) from exc

        return self._to_workspace_response(workspace, WorkspaceRole.OWNER)

    async def list_workspaces(self, user: User) -> list[WorkspaceResponse]:
        result = await self.db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user.id)
            .order_by(Workspace.created_at.desc())
        )
        return [
            self._to_workspace_response(workspace, role)
            for workspace, role in result.all()
        ]

    async def get_workspace(self, workspace: Workspace, membership: WorkspaceMember) -> WorkspaceResponse:
        return self._to_workspace_response(workspace, membership.role)

    async def update_workspace(
        self,
        workspace: Workspace,
        membership: WorkspaceMember,
        data: WorkspaceUpdate,
    ) -> WorkspaceResponse:
        if data.name is not None:
            workspace.name = data.name

        if data.slug is not None:
            new_slug = slugify(data.slug)
            if new_slug != workspace.slug:
                result = await self.db.execute(
                    select(Workspace.id).where(
                        Workspace.slug == new_slug,
                        Workspace.id != workspace.id,
                    )
                )
                if result.scalar_one_or_none() is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Workspace slug already exists",
                    )
                workspace.slug = new_slug

        try:
            await self.db.commit()
            await self.db.refresh(workspace)
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace slug already exists",
            ) from exc

        return self._to_workspace_response(workspace, membership.role)

    async def delete_workspace(self, workspace: Workspace) -> None:
        await self.db.delete(workspace)
        await self.db.commit()

    async def create_invitation(
        self,
        workspace: Workspace,
        inviter: User,
        data: InvitationCreate,
    ) -> InvitationResponse:
        if data.role == WorkspaceRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot invite users as workspace owner",
            )

        email = data.email.lower()

        existing_member = await self.db.execute(
            select(WorkspaceMember)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == workspace.id,
                User.email == email,
            )
        )
        if existing_member.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

        pending = await self.db.execute(
            select(Invitation).where(
                Invitation.workspace_id == workspace.id,
                Invitation.email == email,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > datetime.now(UTC),
            )
        )
        if pending.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this email",
            )

        raw_token = generate_invitation_token()
        invitation = Invitation(
            workspace_id=workspace.id,
            email=email,
            role=data.role,
            token_hash=hash_invitation_token(raw_token),
            invited_by_id=inviter.id,
            expires_at=invitation_expires_at(),
        )
        self.db.add(invitation)
        await self.db.commit()

        return InvitationResponse(
            token=raw_token,
            email=email,
            role=data.role,
            expires_at=invitation.expires_at,
        )

    async def list_members(self, workspace_id: UUID) -> list[WorkspaceMemberResponse]:
        result = await self.db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc())
        )
        return [
            WorkspaceMemberResponse(
                id=member.id,
                user_id=member.user_id,
                email=user.email,
                name=user.name,
                role=member.role,
                created_at=member.created_at,
            )
            for member, user in result.all()
        ]

    async def accept_invitation(self, user: User, raw_token: str) -> AcceptInvitationResponse:
        invitation = await self._get_valid_invitation(raw_token)

        if user.email.lower() != invitation.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invitation email does not match your account",
            )

        existing = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == invitation.workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already a member of this workspace",
            )

        membership = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=user.id,
            role=invitation.role,
        )
        invitation.accepted_at = datetime.now(UTC)
        self.db.add(membership)
        await BudgetService(self.db).create_budget(invitation.workspace_id, user.id)
        await LendingPreferenceService(self.db).create_preference(invitation.workspace_id, user.id)

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already a member of this workspace",
            ) from exc

        result = await self.db.execute(
            select(Workspace).where(Workspace.id == invitation.workspace_id)
        )
        workspace = result.scalar_one()

        return AcceptInvitationResponse(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            role=invitation.role,
        )

    async def _get_valid_invitation(self, raw_token: str) -> Invitation:
        token_hash = hash_invitation_token(raw_token)
        result = await self.db.execute(
            select(Invitation)
            .options(selectinload(Invitation.workspace))
            .where(Invitation.token_hash == token_hash)
        )
        invitation = result.scalar_one_or_none()

        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation token",
            )

        if invitation.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has been revoked",
            )

        if invitation.accepted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted",
            )

        if invitation.expires_at <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

        return invitation

    @staticmethod
    def _to_workspace_response(workspace: Workspace, role: WorkspaceRole) -> WorkspaceResponse:
        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            owner_id=workspace.owner_id,
            role=role,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
