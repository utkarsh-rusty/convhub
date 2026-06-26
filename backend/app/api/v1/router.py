from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.auth.router import auth_router, users_router
from app.conversations.router import conversations_router
from app.workspaces.router import invitations_router, workspaces_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(workspaces_router)
api_router.include_router(invitations_router)
api_router.include_router(conversations_router)
