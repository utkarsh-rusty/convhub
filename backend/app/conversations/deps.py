from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.deps import get_current_user
from app.demo.activation import bind_workspace_demo_context, reset_demo_context
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


@dataclass
class WorkspaceContext:
    workspace_id: UUID
    user: User
    membership: WorkspaceMember


async def get_workspace_context(
    x_workspace_id: UUID = Header(alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncIterator[WorkspaceContext]:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == x_workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    token = await bind_workspace_demo_context(db, x_workspace_id)
    try:
        yield WorkspaceContext(
            workspace_id=x_workspace_id,
            user=current_user,
            membership=membership,
        )
    finally:
        reset_demo_context(token)


async def get_conversation(
    conversation_id: UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == ctx.workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


async def get_participant_conversation(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == ctx.user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation",
        )
    return conversation


async def require_conversation_owner(
    conversation: Conversation = Depends(get_conversation),
    ctx: WorkspaceContext = Depends(get_workspace_context),
) -> Conversation:
    if conversation.owner_id != ctx.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the conversation owner can perform this action",
        )
    return conversation
