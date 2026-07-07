from fastapi import APIRouter

from app.ai.router import chat_router
from app.ai_accounts.router import ai_accounts_router
from app.api.v1.endpoints import health
from app.auth.router import auth_router, users_router
from app.conversations.router import (
    commits_router,
    context_packages_router,
    conversations_router,
)
from app.demo.router import router as demo_router
from app.demo.router import workspace_router as demo_workspace_router
from app.realtime.router import router as realtime_router
from app.resource_management.router import router as credits_router
from app.resource_sharing.router import router as sharing_router
from app.routing.router import router as routing_router
from app.system.router import router as system_router
from app.projects.router import projects_router
from app.repositories.router import repositories_router
from app.repository_branches.router import repository_branches_router
from app.workspaces.router import invitations_router, workspaces_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat_router)
api_router.include_router(ai_accounts_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(workspaces_router)
api_router.include_router(projects_router)
api_router.include_router(repositories_router)
api_router.include_router(repository_branches_router)
api_router.include_router(credits_router)
api_router.include_router(sharing_router)
api_router.include_router(routing_router)
api_router.include_router(invitations_router)
api_router.include_router(conversations_router)
api_router.include_router(commits_router)
api_router.include_router(context_packages_router)
api_router.include_router(demo_router)
api_router.include_router(demo_workspace_router)
api_router.include_router(realtime_router)
api_router.include_router(system_router)
