"""Manual commits and automatic checkpoints for conversations."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.execution import load_execution_summaries
from app.conversations.schemas import (
    CommitCreate,
    CommitDetailResponse,
    CommitListItem,
    CommitMessageSummary,
    CommitRangeMetadata,
    SearchCommitMatch,
)
from app.models.ai_request import AIRequest
from app.models.borrow_record import BorrowRecord
from app.models.conversation import Conversation
from app.models.conversation_checkpoint import ConversationCheckpoint
from app.models.conversation_commit import ConversationCommit
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User


class ConversationCommitService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_checkpoint_for_message(
        self,
        conversation_id: UUID,
        message_id: UUID,
        *,
        commit: bool = False,
    ) -> ConversationCheckpoint:
        """Create an immutable checkpoint for a persisted message.

        When ``commit`` is False, the caller owns the transaction.
        """
        parent_result = await self.db.execute(
            select(ConversationCheckpoint)
            .where(ConversationCheckpoint.conversation_id == conversation_id)
            .order_by(ConversationCheckpoint.created_at.desc(), ConversationCheckpoint.id.desc())
            .limit(1)
        )
        parent = parent_result.scalar_one_or_none()
        checkpoint = ConversationCheckpoint(
            id=uuid4(),
            conversation_id=conversation_id,
            latest_message_id=message_id,
            parent_checkpoint_id=parent.id if parent is not None else None,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        if commit:
            await self.db.commit()
            await self.db.refresh(checkpoint)
        return checkpoint

    async def create_commit(
        self,
        conversation: Conversation,
        user: User,
        data: CommitCreate,
    ) -> CommitDetailResponse:
        message_result = await self.db.execute(
            select(Message).where(
                Message.id == data.latest_message_id,
                Message.conversation_id == conversation.id,
            )
        )
        message = message_result.scalar_one_or_none()
        if message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message does not belong to this conversation",
            )

        checkpoint_result = await self.db.execute(
            select(ConversationCheckpoint)
            .where(
                ConversationCheckpoint.conversation_id == conversation.id,
                ConversationCheckpoint.latest_message_id == data.latest_message_id,
            )
            .order_by(ConversationCheckpoint.created_at.desc())
            .limit(1)
        )
        checkpoint = checkpoint_result.scalar_one_or_none()
        if checkpoint is None:
            checkpoint = await self.create_checkpoint_for_message(
                conversation.id,
                data.latest_message_id,
            )

        existing_commit = await self.db.execute(
            select(ConversationCommit).where(ConversationCommit.checkpoint_id == checkpoint.id)
        )
        if existing_commit.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A commit already exists for this checkpoint",
            )

        parent_result = await self.db.execute(
            select(ConversationCommit)
            .where(ConversationCommit.conversation_id == conversation.id)
            .order_by(ConversationCommit.created_at.desc(), ConversationCommit.id.desc())
            .limit(1)
        )
        parent_commit = parent_result.scalar_one_or_none()

        created_at = datetime.now(UTC)
        commit_hash = self._generate_commit_hash(
            conversation_id=conversation.id,
            checkpoint_id=checkpoint.id,
            parent_commit_id=parent_commit.id if parent_commit is not None else None,
            created_at=created_at,
        )

        # Ensure uniqueness if a rare hash collision occurs.
        for _ in range(5):
            collision = await self.db.execute(
                select(ConversationCommit.id).where(ConversationCommit.commit_hash == commit_hash)
            )
            if collision.scalar_one_or_none() is None:
                break
            created_at = datetime.now(UTC)
            commit_hash = self._generate_commit_hash(
                conversation_id=conversation.id,
                checkpoint_id=checkpoint.id,
                parent_commit_id=parent_commit.id if parent_commit is not None else None,
                created_at=created_at,
            )

        commit = ConversationCommit(
            id=uuid4(),
            commit_hash=commit_hash,
            conversation_id=conversation.id,
            checkpoint_id=checkpoint.id,
            latest_message_id=data.latest_message_id,
            parent_commit_id=parent_commit.id if parent_commit is not None else None,
            title=data.title.strip(),
            description=(data.description.strip() if data.description else None) or None,
            created_by_id=user.id,
            created_at=created_at,
        )
        self.db.add(commit)
        await self.db.commit()
        await self.db.refresh(commit)
        return await self.get_commit_by_hash(commit.commit_hash)

    async def list_commits(self, conversation_id: UUID) -> list[CommitListItem]:
        result = await self.db.execute(
            select(ConversationCommit, User)
            .join(User, User.id == ConversationCommit.created_by_id)
            .where(ConversationCommit.conversation_id == conversation_id)
            .order_by(ConversationCommit.created_at.desc(), ConversationCommit.id.desc())
        )
        rows = list(result.all())
        parent_ids = [
            commit.parent_commit_id for commit, _ in rows if commit.parent_commit_id is not None
        ]
        parent_hashes: dict[UUID, str] = {}
        if parent_ids:
            parent_result = await self.db.execute(
                select(ConversationCommit.id, ConversationCommit.commit_hash).where(
                    ConversationCommit.id.in_(parent_ids)
                )
            )
            parent_hashes = {
                commit_id: commit_hash for commit_id, commit_hash in parent_result.all()
            }
        return [
            CommitListItem(
                commit_hash=commit.commit_hash,
                title=commit.title,
                description=commit.description,
                created_by_id=commit.created_by_id,
                created_by_name=user.name,
                created_at=commit.created_at,
                latest_message_id=commit.latest_message_id,
                parent_commit_id=commit.parent_commit_id,
                parent_commit_hash=(
                    parent_hashes.get(commit.parent_commit_id)
                    if commit.parent_commit_id is not None
                    else None
                ),
            )
            for commit, user in rows
        ]

    async def get_commit_by_hash(self, commit_hash: str) -> CommitDetailResponse:
        result = await self.db.execute(
            select(ConversationCommit, User, Conversation)
            .join(User, User.id == ConversationCommit.created_by_id)
            .join(Conversation, Conversation.id == ConversationCommit.conversation_id)
            .where(ConversationCommit.commit_hash == commit_hash)
        )
        row = result.one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commit not found",
            )
        commit, author, conversation = row

        message_result = await self.db.execute(
            select(Message).where(Message.id == commit.latest_message_id)
        )
        message = message_result.scalar_one()

        parent_hash: str | None = None
        parent_commit: ConversationCommit | None = None
        if commit.parent_commit_id is not None:
            parent_result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == commit.parent_commit_id)
            )
            parent_commit = parent_result.scalar_one_or_none()
            parent_hash = parent_commit.commit_hash if parent_commit is not None else None

        children_result = await self.db.execute(
            select(ConversationCommit)
            .where(ConversationCommit.parent_commit_id == commit.id)
            .order_by(ConversationCommit.created_at.asc())
        )
        children = list(children_result.scalars().all())

        range_metadata = await self._build_range_metadata(parent_commit, commit)

        return CommitDetailResponse(
            id=commit.id,
            commit_hash=commit.commit_hash,
            title=commit.title,
            description=commit.description,
            conversation_id=conversation.id,
            conversation_title=conversation.title,
            workspace_id=conversation.workspace_id,
            checkpoint_id=commit.checkpoint_id,
            latest_message_id=commit.latest_message_id,
            parent_commit_id=commit.parent_commit_id,
            parent_commit_hash=parent_hash,
            child_commit_hashes=[child.commit_hash for child in children],
            created_by_id=author.id,
            created_by_name=author.name,
            created_at=commit.created_at,
            message=CommitMessageSummary(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                author_id=message.author_id,
            ),
            range_metadata=range_metadata,
        )

    async def search_commits(
        self,
        conversation_id: UUID,
        query: str,
    ) -> list[SearchCommitMatch]:
        cleaned = query.strip()
        if not cleaned:
            return []
        pattern = f"%{cleaned}%"
        result = await self.db.execute(
            select(ConversationCommit, User)
            .join(User, User.id == ConversationCommit.created_by_id)
            .where(
                ConversationCommit.conversation_id == conversation_id,
                ConversationCommit.title.ilike(pattern),
            )
            .order_by(ConversationCommit.created_at.desc())
        )
        return [
            SearchCommitMatch(
                commit_hash=commit.commit_hash,
                title=commit.title,
                description=commit.description,
                created_by_name=user.name,
                created_at=commit.created_at,
                latest_message_id=commit.latest_message_id,
            )
            for commit, user in result.all()
        ]

    async def load_commit_counts(self, conversation_ids: list[UUID]) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        result = await self.db.execute(
            select(ConversationCommit.conversation_id, func.count())
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .group_by(ConversationCommit.conversation_id)
        )
        return {conversation_id: count for conversation_id, count in result.all()}

    async def _build_range_metadata(
        self,
        parent_commit: ConversationCommit | None,
        commit: ConversationCommit,
    ) -> CommitRangeMetadata:
        message_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == commit.conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        messages = list(message_result.scalars().all())
        message_ids = [message.id for message in messages]
        start_index = 0
        if parent_commit is not None and parent_commit.latest_message_id in message_ids:
            start_index = message_ids.index(parent_commit.latest_message_id) + 1
        end_index = message_ids.index(commit.latest_message_id) + 1
        range_messages = messages[start_index:end_index]
        range_ids = [message.id for message in range_messages]

        if not range_ids:
            return CommitRangeMetadata(
                providers=[],
                models=[],
                execution_types=[],
                routing_policies=[],
                credits_used="0",
                borrowed_requests=0,
                borrowed_from=[],
            )

        assistant_ids = [
            message.id for message in range_messages if message.role == MessageRole.ASSISTANT
        ]
        execution_map = await load_execution_summaries(self.db, assistant_ids)

        providers: list[str] = []
        models: list[str] = []
        execution_types: list[str] = []
        routing_policies: list[str] = []
        borrowed_from: list[str] = []
        for summary in execution_map.values():
            if summary.provider not in providers:
                providers.append(summary.provider)
            if summary.model not in models:
                models.append(summary.model)
            execution_type = summary.execution_type.value
            if execution_type not in execution_types:
                execution_types.append(execution_type)
            policy = summary.routing_policy.value
            if policy not in routing_policies:
                routing_policies.append(policy)
            if summary.borrowed_from and summary.borrowed_from not in borrowed_from:
                borrowed_from.append(summary.borrowed_from)

        request_result = await self.db.execute(
            select(AIRequest).where(
                AIRequest.conversation_id == commit.conversation_id,
                AIRequest.assistant_message_id.in_(range_ids),
            )
        )
        requests = list(request_result.scalars().all())
        credits = sum((request.estimated_cost or Decimal("0")) for request in requests)
        request_ids = [request.id for request in requests]
        borrowed_requests = 0
        if request_ids:
            borrow_result = await self.db.execute(
                select(func.count()).where(BorrowRecord.request_id.in_(request_ids))
            )
            borrowed_requests = int(borrow_result.scalar_one())

        return CommitRangeMetadata(
            providers=providers,
            models=models,
            execution_types=execution_types,
            routing_policies=routing_policies,
            credits_used=format(credits, "f"),
            borrowed_requests=borrowed_requests,
            borrowed_from=borrowed_from,
        )

    @staticmethod
    def _generate_commit_hash(
        *,
        conversation_id: UUID,
        checkpoint_id: UUID,
        parent_commit_id: UUID | None,
        created_at: datetime,
    ) -> str:
        payload = (
            f"{conversation_id}:{checkpoint_id}:{parent_commit_id or ''}:{created_at.isoformat()}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:7]
