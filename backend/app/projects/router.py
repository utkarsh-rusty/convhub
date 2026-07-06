from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.conversations.schemas import ConversationResponse
from app.models.project import Project
from app.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.projects.service import ProjectService

projects_router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db=db)


async def get_project(
    project_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == ctx.workspace_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@projects_router.get("", response_model=list[ProjectResponse])
async def list_projects(
    include_archived: bool = Query(default=False),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return await service.list_projects(
        ctx.workspace_id,
        include_archived=include_archived,
    )


@projects_router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.create_project(ctx, data)


@projects_router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(
    project: Project = Depends(get_project),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.get_project(project, include_details=True)


@projects_router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    data: ProjectUpdate,
    project: Project = Depends(get_project),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.update_project(project, data)


@projects_router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project: Project = Depends(get_project),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.archive_project(project)


@projects_router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project: Project = Depends(get_project),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.restore_project(project)


@projects_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project: Project = Depends(get_project),
    service: ProjectService = Depends(get_project_service),
) -> None:
    await service.delete_project(project)


@projects_router.get(
    "/{project_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_project_conversations(
    project: Project = Depends(get_project),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: ProjectService = Depends(get_project_service),
) -> list[ConversationResponse]:
    return await service.list_project_conversations(project, ctx.user.id)
