from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import ConversationResponse
from app.conversations.service import ConversationService
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.message import Message
from app.models.project import DEFAULT_PROJECT_NAME, Project
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.projects.schemas import (
    ProjectConversationSummary,
    ProjectCreate,
    ProjectMemberSummary,
    ProjectResponse,
    ProjectUpdate,
)


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_default_project(
        self,
        workspace_id: UUID,
        created_by_id: UUID,
        *,
        commit: bool = False,
    ) -> Project:
        project = Project(
            workspace_id=workspace_id,
            name=DEFAULT_PROJECT_NAME,
            description="Default project for workspace conversations",
            created_by_id=created_by_id,
        )
        self.db.add(project)
        await self.db.flush()
        if commit:
            await self.db.commit()
            await self.db.refresh(project)
        return project

    async def get_or_create_default_project(
        self,
        workspace_id: UUID,
        created_by_id: UUID,
    ) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.workspace_id == workspace_id,
                Project.name == DEFAULT_PROJECT_NAME,
                Project.archived_at.is_(None),
            )
        )
        project = result.scalar_one_or_none()
        if project is not None:
            return project

        any_default = await self.db.execute(
            select(Project).where(
                Project.workspace_id == workspace_id,
                Project.name == DEFAULT_PROJECT_NAME,
            )
        )
        project = any_default.scalar_one_or_none()
        if project is not None:
            return project

        return await self.create_default_project(workspace_id, created_by_id)

    async def resolve_project_for_workspace(
        self,
        workspace_id: UUID,
        project_id: UUID | None,
        *,
        created_by_id: UUID,
        allow_archived: bool = False,
    ) -> Project:
        if project_id is None:
            return await self.get_or_create_default_project(workspace_id, created_by_id)

        project = await self._load_project(project_id, workspace_id)
        if project.archived_at is not None and not allow_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use an archived project",
            )
        return project

    async def create_project(
        self,
        ctx: WorkspaceContext,
        data: ProjectCreate,
    ) -> ProjectResponse:
        project = Project(
            workspace_id=ctx.workspace_id,
            name=data.name.strip(),
            description=data.description,
            icon=data.icon,
            color=data.color,
            created_by_id=ctx.user.id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return await self._to_response(project, include_details=False)

    async def list_projects(
        self,
        workspace_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[ProjectResponse]:
        query = select(Project).where(Project.workspace_id == workspace_id)
        if not include_archived:
            query = query.where(Project.archived_at.is_(None))
        query = query.order_by(Project.name.asc(), Project.created_at.asc())
        result = await self.db.execute(query)
        projects = list(result.scalars().all())
        return [await self._to_response(project, include_details=False) for project in projects]

    async def get_project(
        self,
        project: Project,
        *,
        include_details: bool = True,
    ) -> ProjectResponse:
        return await self._to_response(project, include_details=include_details)

    async def update_project(
        self,
        project: Project,
        data: ProjectUpdate,
    ) -> ProjectResponse:
        if data.name is not None:
            project.name = data.name.strip()
        if data.description is not None:
            project.description = data.description
        if data.icon is not None:
            project.icon = data.icon
        if data.color is not None:
            project.color = data.color
        await self.db.commit()
        await self.db.refresh(project)
        return await self._to_response(project, include_details=False)

    async def archive_project(self, project: Project) -> ProjectResponse:
        if project.archived_at is None:
            project.archived_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(project)
        return await self._to_response(project, include_details=False)

    async def restore_project(self, project: Project) -> ProjectResponse:
        if project.archived_at is not None:
            project.archived_at = None
            await self.db.commit()
            await self.db.refresh(project)
        return await self._to_response(project, include_details=False)

    async def delete_project(self, project: Project) -> None:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.project_id == project.id)
        )
        conversation_count = int(count_result.scalar_one())
        if conversation_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a project that contains conversations",
            )
        await self.db.delete(project)
        await self.db.commit()

    async def list_project_conversations(
        self,
        project: Project,
        viewer_user_id: UUID,
    ) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.project_id == project.id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        conversations = list(result.scalars().all())
        return await ConversationService(self.db)._build_conversation_responses(
            conversations,
            viewer_user_id=viewer_user_id,
        )

    async def _load_project(self, project_id: UUID, workspace_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def _to_response(
        self,
        project: Project,
        *,
        include_details: bool,
    ) -> ProjectResponse:
        conversation_count, branch_count, commit_count, package_count, last_activity = (
            await self._load_counts(project.id)
        )
        created_by_name = project.created_by.name if project.created_by is not None else None

        members: list[ProjectMemberSummary] = []
        recent: list[ProjectConversationSummary] = []
        if include_details:
            members = await self._load_members(project.workspace_id)
            recent = await self._load_recent_conversations(project.id)

        return ProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            icon=project.icon,
            color=project.color,
            created_by_id=project.created_by_id,
            created_by_name=created_by_name,
            created_at=project.created_at,
            updated_at=project.updated_at,
            archived_at=project.archived_at,
            is_default=project.name == DEFAULT_PROJECT_NAME,
            conversation_count=conversation_count,
            branch_count=branch_count,
            commit_count=commit_count,
            context_package_count=package_count,
            last_activity_at=last_activity,
            members=members,
            recent_conversations=recent,
        )

    async def _load_counts(
        self,
        project_id: UUID,
    ) -> tuple[int, int, int, int, datetime | None]:
        conversation_result = await self.db.execute(
            select(
                func.count(Conversation.id),
                func.coalesce(
                    func.sum(
                        case(
                            (Conversation.parent_conversation_id.is_not(None), 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.max(Conversation.last_activity_at),
            ).where(
                Conversation.project_id == project_id,
                Conversation.archived_at.is_(None),
            )
        )
        conversation_count, branch_count, last_activity = conversation_result.one()

        commit_result = await self.db.execute(
            select(func.count(ConversationCommit.id))
            .select_from(ConversationCommit)
            .join(Conversation, Conversation.id == ConversationCommit.conversation_id)
            .where(Conversation.project_id == project_id)
        )
        commit_count = int(commit_result.scalar_one())

        package_result = await self.db.execute(
            select(func.count(ContextPackage.id))
            .select_from(ContextPackage)
            .join(Conversation, Conversation.id == ContextPackage.conversation_id)
            .where(Conversation.project_id == project_id)
        )
        package_count = int(package_result.scalar_one())

        return (
            int(conversation_count or 0),
            int(branch_count or 0),
            commit_count,
            package_count,
            last_activity,
        )

    async def _load_members(self, workspace_id: UUID) -> list[ProjectMemberSummary]:
        result = await self.db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(User.name.asc())
        )
        return [
            ProjectMemberSummary(
                user_id=user.id,
                name=user.name,
                email=user.email,
                role=member.role.value,
            )
            for member, user in result.all()
        ]

    async def _load_recent_conversations(
        self,
        project_id: UUID,
        *,
        limit: int = 8,
    ) -> list[ProjectConversationSummary]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.project_id == project_id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
            .limit(limit)
        )
        conversations = list(result.scalars().all())
        if not conversations:
            return []

        conversation_ids = [item.id for item in conversations]
        message_counts = await self.db.execute(
            select(Message.conversation_id, func.count())
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
        )
        message_map = {row[0]: int(row[1]) for row in message_counts.all()}

        commit_counts = await self.db.execute(
            select(ConversationCommit.conversation_id, func.count())
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .group_by(ConversationCommit.conversation_id)
        )
        commit_map = {row[0]: int(row[1]) for row in commit_counts.all()}

        return [
            ProjectConversationSummary(
                id=conversation.id,
                title=conversation.title,
                branch_name=conversation.branch_name,
                parent_conversation_id=conversation.parent_conversation_id,
                last_activity_at=conversation.last_activity_at,
                message_count=message_map.get(conversation.id, 0),
                commit_count=commit_map.get(conversation.id, 0),
                is_restored=conversation.restored_from_package_id is not None,
            )
            for conversation in conversations
        ]
