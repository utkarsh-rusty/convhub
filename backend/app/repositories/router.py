from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.conversations.deps import WorkspaceContext, get_workspace_context
from app.conversations.schemas import ConversationResponse
from app.models.repository import Repository
from app.repositories.schemas import RepositoryCreate, RepositoryResponse, RepositoryUpdate
from app.repositories.service import RepositoryService

repositories_router = APIRouter(prefix="/repositories", tags=["repositories"])


def get_repository_service(db: AsyncSession = Depends(get_db)) -> RepositoryService:
    return RepositoryService(db=db)


async def get_repository(
    repository_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Repository:
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.workspace_id == ctx.workspace_id,
        )
    )
    repository = result.scalar_one_or_none()
    if repository is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repository


@repositories_router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    project_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: RepositoryService = Depends(get_repository_service),
) -> list[RepositoryResponse]:
    return await service.list_repositories(
        ctx.workspace_id,
        project_id=project_id,
        include_archived=include_archived,
    )


@repositories_router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository(
    data: RepositoryCreate,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    return await service.create_repository(ctx, data)


@repositories_router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository_detail(
    repository: Repository = Depends(get_repository),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    return await service.get_repository(repository, include_details=True)


@repositories_router.patch("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    data: RepositoryUpdate,
    repository: Repository = Depends(get_repository),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    return await service.update_repository(repository, data)


@repositories_router.post("/{repository_id}/archive", response_model=RepositoryResponse)
async def archive_repository(
    repository: Repository = Depends(get_repository),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    return await service.archive_repository(repository)


@repositories_router.post("/{repository_id}/restore", response_model=RepositoryResponse)
async def restore_repository(
    repository: Repository = Depends(get_repository),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    return await service.restore_repository(repository)


@repositories_router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository: Repository = Depends(get_repository),
    service: RepositoryService = Depends(get_repository_service),
) -> None:
    await service.delete_repository(repository)


@repositories_router.get(
    "/{repository_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_repository_conversations(
    repository: Repository = Depends(get_repository),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    service: RepositoryService = Depends(get_repository_service),
) -> list[ConversationResponse]:
    return await service.list_repository_conversations(repository, ctx.user.id)


from app.external_ai_sessions.router import register_repository_external_ai_session_routes
from app.repository_branches.router import register_repository_branch_routes
from app.workspace_client.router import register_repository_workspace_client_routes
from app.workspace_sessions.router import register_repository_workspace_session_routes

register_repository_branch_routes(repositories_router)
register_repository_workspace_session_routes(repositories_router)
register_repository_workspace_client_routes(repositories_router)
register_repository_external_ai_session_routes(repositories_router)
