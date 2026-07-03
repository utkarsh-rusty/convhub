from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.execution import load_execution_summaries
from app.conversations.schemas import (
    ConversationBranchCreate,
    ConversationCreate,
    ConversationLineageResponse,
    ConversationOwnerSummary,
    ConversationParticipantCreate,
    ConversationParticipantResponse,
    ConversationParticipantSummary,
    ConversationResponse,
    ConversationSummary,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.models.conversation import DEFAULT_CONVERSATION_TITLE, Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import ConversationParticipantRole, MessageRole
from app.models.message import Message
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.realtime.broadcaster import get_broadcaster


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(
        self,
        ctx: WorkspaceContext,
        data: ConversationCreate,
    ) -> ConversationResponse:
        now = datetime.now(UTC)
        conversation = Conversation(
            workspace_id=ctx.workspace_id,
            created_by_id=ctx.user.id,
            owner_id=ctx.user.id,
            title=data.title or DEFAULT_CONVERSATION_TITLE,
            last_activity_at=now,
        )
        owner = ConversationParticipant(
            conversation=conversation,
            user_id=ctx.user.id,
            role=ConversationParticipantRole.OWNER,
            joined_at=now,
        )
        self.db.add(conversation)
        self.db.add(owner)
        await self.db.commit()
        await self.db.refresh(conversation)
        return self._to_conversation_response(
            conversation,
            [self._participant_summary(ctx.user, ConversationParticipantRole.OWNER)],
            viewer_user_id=ctx.user.id,
            owner_name=ctx.user.name,
        )

    async def list_conversations(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.archived_at.is_(None),
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        conversations = list(result.scalars().all())
        conversation_ids = [conversation.id for conversation in conversations]
        participant_map = await self._load_participant_summaries(conversation_ids)
        owner_names = await self._load_owner_names(
            [conversation.owner_id for conversation in conversations]
        )
        return [
            self._to_conversation_response(
                conversation,
                participant_map.get(conversation.id, []),
                viewer_user_id=user_id,
                owner_name=owner_names.get(conversation.owner_id),
            )
            for conversation in conversations
        ]

    async def get_conversation(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> ConversationResponse:
        participants = await self._load_participant_summaries([conversation.id])
        owner_names = await self._load_owner_names([conversation.owner_id])
        return self._to_conversation_response(
            conversation,
            participants.get(conversation.id, []),
            viewer_user_id=viewer_user_id,
            owner_name=owner_names.get(conversation.owner_id),
        )

    async def update_conversation(
        self,
        conversation: Conversation,
        data: ConversationUpdate,
        *,
        viewer_user_id: UUID | None = None,
    ) -> ConversationResponse:
        if data.title is not None:
            conversation.title = data.title

        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation, viewer_user_id=viewer_user_id)

    async def delete_conversation(self, conversation: Conversation) -> None:
        if conversation.archived_at is None:
            conversation.archived_at = datetime.now(UTC)
            await self.db.commit()

    async def archive_conversation(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> ConversationResponse:
        if conversation.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is already archived",
            )
        conversation.archived_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation, viewer_user_id=viewer_user_id)

    async def restore_conversation(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> ConversationResponse:
        if conversation.archived_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not archived",
            )
        conversation.archived_at = None
        conversation.last_activity_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation, viewer_user_id=viewer_user_id)

    async def list_participants(
        self,
        conversation_id: UUID,
    ) -> list[ConversationParticipantResponse]:
        result = await self.db.execute(
            select(ConversationParticipant, User)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == conversation_id)
            .order_by(ConversationParticipant.joined_at.asc())
        )
        return [
            ConversationParticipantResponse(
                conversation_id=participant.conversation_id,
                user_id=participant.user_id,
                name=user.name,
                email=user.email,
                role=participant.role,
                joined_at=participant.joined_at,
            )
            for participant, user in result.all()
        ]

    async def add_participants(
        self,
        conversation: Conversation,
        data: ConversationParticipantCreate,
    ) -> list[ConversationParticipantResponse]:
        unique_user_ids = list(dict.fromkeys(data.user_ids))
        workspace_members = await self._get_workspace_member_ids(conversation.workspace_id)
        existing_participants = await self._get_participant_user_ids(conversation.id)

        for user_id in unique_user_ids:
            if user_id not in workspace_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must belong to the workspace",
                )
            if user_id in existing_participants:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a participant in this conversation",
                )

            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_id,
                role=ConversationParticipantRole.MEMBER,
            )
            self.db.add(participant)

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a participant in this conversation",
            ) from exc

        return await self.list_participants(conversation.id)

    async def remove_participant(
        self,
        conversation: Conversation,
        user_id: UUID,
    ) -> None:
        if user_id == conversation.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation owners cannot be removed",
            )

        result = await self.db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation.id,
                ConversationParticipant.user_id == user_id,
            )
        )
        participant = result.scalar_one_or_none()
        if participant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant not found",
            )

        participant_ids = await self._get_participant_user_ids(conversation.id)
        if len(participant_ids) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last participant",
            )

        await self.db.delete(participant)
        await self.db.commit()

        broadcaster = get_broadcaster()
        if broadcaster is not None:
            await broadcaster.conversation_updated(
                conversation.workspace_id,
                conversation.id,
                {"participant_removed": str(user_id)},
            )

    async def create_message(
        self,
        conversation: Conversation,
        user: User,
        data: MessageCreate,
    ) -> MessageResponse:
        if data.role != MessageRole.USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only user messages can be created via the API",
            )

        now = datetime.now(UTC)
        message = Message(
            conversation_id=conversation.id,
            author_id=user.id,
            role=MessageRole.USER,
            content=data.content,
        )
        conversation.last_activity_at = now
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        response = MessageResponse.model_validate(message)
        broadcaster = get_broadcaster()
        if broadcaster is not None:
            await broadcaster.message_created(
                conversation.workspace_id,
                conversation.id,
                response.model_dump(mode="json"),
            )
            await broadcaster.conversation_updated(
                conversation.workspace_id,
                conversation.id,
                {"last_activity_at": now.isoformat()},
            )
        return response

    async def list_messages(self, conversation_id: UUID) -> list[MessageResponse]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())
        assistant_ids = [
            message.id for message in messages if message.role == MessageRole.ASSISTANT
        ]
        execution_map = await load_execution_summaries(self.db, assistant_ids)

        return [
            MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                author_id=message.author_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                provider=(
                    execution.provider if (execution := execution_map.get(message.id)) else None
                ),
                execution=execution_map.get(message.id),
            )
            for message in messages
        ]

    async def _get_workspace_member_ids(self, workspace_id: UUID) -> set[UUID]:
        result = await self.db.execute(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return set(result.scalars().all())

    async def _get_participant_user_ids(self, conversation_id: UUID) -> set[UUID]:
        result = await self.db.execute(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id
            )
        )
        return set(result.scalars().all())

    async def _load_participant_summaries(
        self,
        conversation_ids: list[UUID],
    ) -> dict[UUID, list[ConversationParticipantSummary]]:
        if not conversation_ids:
            return {}

        result = await self.db.execute(
            select(ConversationParticipant, User)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id.in_(conversation_ids))
            .order_by(ConversationParticipant.joined_at.asc())
        )

        participant_map: dict[UUID, list[ConversationParticipantSummary]] = {}
        for participant, user in result.all():
            participant_map.setdefault(participant.conversation_id, []).append(
                self._participant_summary(user, participant.role)
            )
        return participant_map

    async def _load_owner_names(self, owner_ids: list[UUID]) -> dict[UUID, str]:
        unique_ids = list({owner_id for owner_id in owner_ids if owner_id is not None})
        if not unique_ids:
            return {}
        result = await self.db.execute(select(User).where(User.id.in_(unique_ids)))
        return {user.id: user.name for user in result.scalars().all()}

    @staticmethod
    def _participant_summary(
        user: User, role: ConversationParticipantRole
    ) -> ConversationParticipantSummary:
        return ConversationParticipantSummary(
            user_id=user.id,
            name=user.name,
            role=role,
        )

    @staticmethod
    def _to_conversation_response(
        conversation: Conversation,
        participants: list[ConversationParticipantSummary],
        *,
        viewer_user_id: UUID | None = None,
        owner_name: str | None = None,
    ) -> ConversationResponse:
        is_participant = viewer_user_id is not None and any(
            participant.user_id == viewer_user_id for participant in participants
        )
        resolved_owner_name = owner_name
        if resolved_owner_name is None:
            for participant in participants:
                if participant.user_id == conversation.owner_id:
                    resolved_owner_name = participant.name
                    break
        owner = (
            ConversationOwnerSummary(user_id=conversation.owner_id, name=resolved_owner_name)
            if resolved_owner_name is not None
            else None
        )
        return ConversationResponse(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            created_by_id=conversation.created_by_id,
            owner_id=conversation.owner_id,
            owner=owner,
            title=conversation.title,
            last_activity_at=conversation.last_activity_at,
            archived_at=conversation.archived_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            parent_conversation_id=conversation.parent_conversation_id,
            branch_from_message_id=conversation.branch_from_message_id,
            branch_name=conversation.branch_name,
            is_participant=is_participant,
            participant_count=len(participants),
            participants=participants,
        )

    async def create_branch(
        self,
        parent_conversation: Conversation,
        ctx: WorkspaceContext,
        data: ConversationBranchCreate,
    ) -> ConversationResponse:
        result = await self.db.execute(
            select(Message).where(
                Message.id == data.message_id,
                Message.conversation_id == parent_conversation.id,
            )
        )
        branch_from_message = result.scalar_one_or_none()
        if branch_from_message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message does not belong to this conversation",
            )

        messages_result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == parent_conversation.id,
                Message.created_at <= branch_from_message.created_at,
            )
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        source_messages = list(messages_result.scalars().all())
        cutoff_index = next(
            (
                index
                for index, msg in enumerate(source_messages)
                if msg.id == branch_from_message.id
            ),
            None,
        )
        if cutoff_index is None:
            source_messages_to_copy = source_messages
        else:
            source_messages_to_copy = source_messages[: cutoff_index + 1]

        now = datetime.now(UTC)
        branch_title = self._compose_branch_title(parent_conversation.title, data.branch_name)
        branch = Conversation(
            workspace_id=parent_conversation.workspace_id,
            project_id=parent_conversation.project_id,
            created_by_id=ctx.user.id,
            owner_id=ctx.user.id,
            title=branch_title,
            last_activity_at=now,
            parent_conversation_id=parent_conversation.id,
            branch_from_message_id=branch_from_message.id,
            branch_name=data.branch_name,
        )
        self.db.add(branch)
        await self.db.flush()

        self.db.add(
            ConversationParticipant(
                conversation_id=branch.id,
                user_id=ctx.user.id,
                role=ConversationParticipantRole.OWNER,
                joined_at=now,
            )
        )

        for source_message in source_messages_to_copy:
            self.db.add(
                Message(
                    conversation_id=branch.id,
                    author_id=source_message.author_id,
                    role=source_message.role,
                    content=source_message.content,
                    created_at=source_message.created_at,
                )
            )

        await self.db.commit()
        await self.db.refresh(branch)
        return await self.get_conversation(branch, viewer_user_id=ctx.user.id)

    async def list_branches(
        self,
        parent_conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.parent_conversation_id == parent_conversation.id)
            .order_by(Conversation.created_at.asc())
        )
        branches = list(result.scalars().all())
        participant_map = await self._load_participant_summaries([branch.id for branch in branches])
        owner_names = await self._load_owner_names([branch.owner_id for branch in branches])
        return [
            self._to_conversation_response(
                branch,
                participant_map.get(branch.id, []),
                viewer_user_id=viewer_user_id,
                owner_name=owner_names.get(branch.owner_id),
            )
            for branch in branches
        ]

    async def get_lineage(self, conversation: Conversation) -> ConversationLineageResponse:
        chain: list[Conversation] = [conversation]
        seen_ids: set[UUID] = {conversation.id}
        cursor = conversation
        while cursor.parent_conversation_id is not None:
            parent_result = await self.db.execute(
                select(Conversation).where(Conversation.id == cursor.parent_conversation_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None or parent.id in seen_ids:
                break
            seen_ids.add(parent.id)
            chain.append(parent)
            cursor = parent

        chain.reverse()
        root = chain[0]
        ancestors = chain[1:-1] if len(chain) > 2 else []
        return ConversationLineageResponse(
            root=ConversationSummary.model_validate(root),
            ancestors=[ConversationSummary.model_validate(item) for item in ancestors],
            current=ConversationSummary.model_validate(conversation),
        )

    @staticmethod
    def _compose_branch_title(parent_title: str, branch_name: str | None) -> str:
        cleaned = (branch_name or "").strip()
        if cleaned:
            candidate = f"{parent_title} · {cleaned}"
        else:
            candidate = f"{parent_title} (branch)"
        return candidate[:255]
