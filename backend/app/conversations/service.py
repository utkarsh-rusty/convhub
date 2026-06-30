from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.deps import WorkspaceContext
from app.conversations.execution import load_execution_summaries
from app.conversations.schemas import (
    ConversationCreate,
    ConversationParticipantCreate,
    ConversationParticipantResponse,
    ConversationParticipantSummary,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.models.conversation import DEFAULT_CONVERSATION_TITLE, Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import ConversationParticipantRole, MessageRole
from app.models.message import Message
from app.models.user import User
from app.realtime.broadcaster import get_broadcaster
from app.models.workspace_member import WorkspaceMember


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
        )

    async def list_conversations(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[ConversationResponse]:
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.archived_at.is_(None),
                ConversationParticipant.user_id == user_id,
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        conversations = list(result.scalars().all())
        participant_map = await self._load_participant_summaries(
            [conversation.id for conversation in conversations]
        )
        return [
            self._to_conversation_response(conversation, participant_map.get(conversation.id, []))
            for conversation in conversations
        ]

    async def get_conversation(self, conversation: Conversation) -> ConversationResponse:
        participants = await self._load_participant_summaries([conversation.id])
        return self._to_conversation_response(
            conversation,
            participants.get(conversation.id, []),
        )

    async def update_conversation(
        self,
        conversation: Conversation,
        data: ConversationUpdate,
    ) -> ConversationResponse:
        if data.title is not None:
            conversation.title = data.title

        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation)

    async def delete_conversation(self, conversation: Conversation) -> None:
        if conversation.archived_at is None:
            conversation.archived_at = datetime.now(UTC)
            await self.db.commit()

    async def archive_conversation(self, conversation: Conversation) -> ConversationResponse:
        if conversation.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is already archived",
            )
        conversation.archived_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation)

    async def restore_conversation(self, conversation: Conversation) -> ConversationResponse:
        if conversation.archived_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not archived",
            )
        conversation.archived_at = None
        conversation.last_activity_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation)

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
        if participant.role == ConversationParticipantRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation owners cannot be removed",
            )

        await self.db.delete(participant)
        await self.db.commit()

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
                provider=execution.provider if (execution := execution_map.get(message.id)) else None,
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

    @staticmethod
    def _participant_summary(user: User, role: ConversationParticipantRole) -> ConversationParticipantSummary:
        return ConversationParticipantSummary(
            user_id=user.id,
            name=user.name,
            role=role,
        )

    @staticmethod
    def _to_conversation_response(
        conversation: Conversation,
        participants: list[ConversationParticipantSummary],
    ) -> ConversationResponse:
        return ConversationResponse(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            created_by_id=conversation.created_by_id,
            title=conversation.title,
            last_activity_at=conversation.last_activity_at,
            archived_at=conversation.archived_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            participant_count=len(participants),
            participants=participants,
        )
