"""Deterministic Context Package restore into new working conversations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import (
    ContextRestoreRequest,
    ConversationParticipantSummary,
    ConversationResponse,
    ConversationRestoreInfoResponse,
)
from app.conversations.service import ConversationService
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import ConversationParticipantRole, MessageRole
from app.models.message import Message
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.projects.service import ProjectService


class ContextRestoreService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conversations = ConversationService(db)

    async def restore(
        self,
        package_id: UUID,
        ctx: WorkspaceContext,
        data: ContextRestoreRequest,
    ) -> ConversationResponse:
        package = await self._load_package(package_id, ctx.workspace_id)
        metadata = package.metadata_json or {}
        summary = package.summary_json or {}
        conversation_meta = metadata.get("conversation") or {}
        commit_meta = metadata.get("commit") or {}
        participants_meta = metadata.get("participants") or []

        source_conversation_id = package.conversation_id
        source_commit_id = package.commit_id

        source_project_id = None
        source_result = await self.db.execute(
            select(Conversation).where(Conversation.id == source_conversation_id)
        )
        source_conversation = source_result.scalar_one_or_none()
        if source_conversation is not None:
            source_project_id = source_conversation.project_id

        project = await ProjectService(self.db).resolve_project_for_workspace(
            ctx.workspace_id,
            data.project_id or source_project_id,
            created_by_id=ctx.user.id,
        )

        now = datetime.now(UTC)
        title = (data.conversation_name or "").strip()
        if not title:
            commit_title = str(commit_meta.get("title") or "Restored checkpoint")
            title = f"Restored: {commit_title}"[:255]

        branch_name = None
        parent_conversation_id = None
        branch_from_message_id = None
        if data.restore_metadata:
            branch_name = conversation_meta.get("branch_name")
            # Do not attach to original parent branch lineage; restore is a new working copy.
            parent_conversation_id = None
            branch_from_message_id = None

        # Owner is always the restoring user for the new working conversation.
        conversation = Conversation(
            id=uuid4(),
            workspace_id=ctx.workspace_id,
            project_id=project.id,
            created_by_id=ctx.user.id,
            owner_id=ctx.user.id,
            title=title,
            last_activity_at=now,
            branch_name=branch_name,
            parent_conversation_id=parent_conversation_id,
            branch_from_message_id=branch_from_message_id,
            restored_from_package_id=package.id,
            restored_from_commit_id=source_commit_id,
            restored_from_conversation_id=source_conversation_id,
            restored_by_user_id=ctx.user.id,
            restored_at=now,
        )
        self.db.add(conversation)
        await self.db.flush()

        await self._restore_participants(
            conversation=conversation,
            participants_meta=participants_meta,
            requesting_user=ctx.user,
            restore_participants=data.restore_participants,
            restore_only_self=data.restore_only_self,
            now=now,
        )

        if data.restore_messages:
            await self._restore_messages(conversation, summary, now=now)

        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.conversations.get_conversation(
            conversation,
            viewer_user_id=ctx.user.id,
        )

    async def get_restore_info(
        self,
        conversation: Conversation,
        workspace_id: UUID,
    ) -> ConversationRestoreInfoResponse:
        if conversation.restored_from_package_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation was not restored from a context package",
            )

        package_result = await self.db.execute(
            select(ContextPackage).where(
                ContextPackage.id == conversation.restored_from_package_id
            )
        )
        package = package_result.scalar_one_or_none()
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source context package not found",
            )

        commit_result = await self.db.execute(
            select(ConversationCommit).where(
                ConversationCommit.id == conversation.restored_from_commit_id
            )
        )
        commit = commit_result.scalar_one_or_none()

        source_conversation = None
        if conversation.restored_from_conversation_id is not None:
            source_result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == conversation.restored_from_conversation_id,
                    Conversation.workspace_id == workspace_id,
                )
            )
            source_conversation = source_result.scalar_one_or_none()

        restored_by_name = None
        if conversation.restored_by_user_id is not None:
            user_result = await self.db.execute(
                select(User).where(User.id == conversation.restored_by_user_id)
            )
            restored_by = user_result.scalar_one_or_none()
            restored_by_name = restored_by.name if restored_by else None

        return ConversationRestoreInfoResponse(
            conversation_id=conversation.id,
            is_restored=True,
            restored_at=conversation.restored_at,
            restored_by_user_id=conversation.restored_by_user_id,
            restored_by_name=restored_by_name,
            original_conversation_id=conversation.restored_from_conversation_id,
            original_conversation_title=(
                source_conversation.title if source_conversation is not None else None
            ),
            original_commit_id=conversation.restored_from_commit_id,
            original_commit_hash=commit.commit_hash if commit is not None else None,
            original_commit_title=commit.title if commit is not None else None,
            context_package_id=package.id,
            context_package_version=package.version,
            context_package_status=package.status,
        )

    async def _load_package(self, package_id: UUID, workspace_id: UUID) -> ContextPackage:
        result = await self.db.execute(
            select(ContextPackage).where(ContextPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context package not found",
            )

        conversation_result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == package.conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        if conversation_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context package not found",
            )
        return package

    async def _restore_participants(
        self,
        *,
        conversation: Conversation,
        participants_meta: list[Any],
        requesting_user: User,
        restore_participants: bool,
        restore_only_self: bool,
        now: datetime,
    ) -> None:
        self.db.add(
            ConversationParticipant(
                conversation_id=conversation.id,
                user_id=requesting_user.id,
                role=ConversationParticipantRole.OWNER,
                joined_at=now,
            )
        )

        if restore_only_self or not restore_participants:
            return

        workspace_members = await self.db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == conversation.workspace_id
            )
        )
        member_ids = set(workspace_members.scalars().all())

        for item in participants_meta:
            if not isinstance(item, dict):
                continue
            user_id_raw = item.get("user_id")
            if not user_id_raw:
                continue
            try:
                user_id = UUID(str(user_id_raw))
            except ValueError:
                continue
            if user_id == requesting_user.id:
                continue
            if user_id not in member_ids:
                continue
            role_value = str(item.get("role") or "member")
            role = (
                ConversationParticipantRole.OWNER
                if role_value == "owner"
                else ConversationParticipantRole.MEMBER
            )
            # Restoring user remains the sole owner of the new conversation.
            if role == ConversationParticipantRole.OWNER:
                role = ConversationParticipantRole.MEMBER
            self.db.add(
                ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=user_id,
                    role=role,
                    joined_at=now,
                )
            )

    async def _restore_messages(
        self,
        conversation: Conversation,
        summary: dict[str, Any],
        *,
        now: datetime,
    ) -> None:
        snapshot = summary.get("conversation_snapshot") or []
        if not isinstance(snapshot, list):
            return

        latest_activity = conversation.last_activity_at or now
        for item in snapshot:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "")
            if not content:
                continue
            role_value = str(item.get("role") or "user")
            try:
                role = MessageRole(role_value)
            except ValueError:
                role = MessageRole.USER

            author_id = None
            author_raw = item.get("author_id")
            if author_raw:
                try:
                    author_id = UUID(str(author_raw))
                except ValueError:
                    author_id = None

            created_at = now
            created_at_raw = item.get("created_at")
            if created_at_raw:
                try:
                    created_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                except ValueError:
                    created_at = now

            message = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                author_id=author_id,
                role=role,
                content=content,
                created_at=created_at,
            )
            self.db.add(message)
            if created_at > latest_activity:
                latest_activity = created_at

        conversation.last_activity_at = latest_activity
