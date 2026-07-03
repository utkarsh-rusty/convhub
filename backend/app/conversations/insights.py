"""Read-only branch visualization and comparison helpers."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.schemas import (
    BranchTreeNode,
    BranchTreeResponse,
    ComparisonMessage,
    ConversationCompareResponse,
    ConversationSearchResponse,
    ConversationStatsResponse,
    ConversationTimelineResponse,
    SearchMessageMatch,
    TimelineEvent,
)
from app.models.ai_request import AIRequest
from app.models.borrow_record import BorrowRecord
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User


class ConversationInsightsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_branch_tree(self, conversation: Conversation) -> BranchTreeResponse:
        root = await self._find_root(conversation)
        descendants = await self._load_descendants(root.id, root.workspace_id)
        nodes = [root, *descendants]
        owner_names = await self._load_user_names([node.owner_id for node in nodes])
        message_counts = await self._load_message_counts([node.id for node in nodes])
        participant_counts = await self._load_participant_counts([node.id for node in nodes])

        node_map: dict[UUID, BranchTreeNode] = {}
        for node in nodes:
            node_map[node.id] = BranchTreeNode(
                id=node.id,
                title=node.title,
                branch_name=node.branch_name,
                parent_conversation_id=node.parent_conversation_id,
                owner_id=node.owner_id,
                owner_name=owner_names.get(node.owner_id),
                latest_activity_at=node.last_activity_at,
                message_count=message_counts.get(node.id, 0),
                participant_count=participant_counts.get(node.id, 0),
                children=[],
            )

        for node in nodes:
            parent_id = node.parent_conversation_id
            if parent_id is not None and parent_id in node_map and node.id != root.id:
                node_map[parent_id].children.append(node_map[node.id])

        for tree_node in node_map.values():
            tree_node.children.sort(key=lambda child: child.latest_activity_at, reverse=True)

        return BranchTreeResponse(root=node_map[root.id])

    async def compare(
        self,
        left: Conversation,
        right: Conversation,
    ) -> ConversationCompareResponse:
        if left.workspace_id != right.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversations must belong to the same workspace",
            )

        left_ancestors = await self._ancestor_chain(left)
        right_ancestors = await self._ancestor_chain(right)
        right_ids = {conversation.id for conversation in right_ancestors}
        common_ancestor = next(
            (conversation for conversation in left_ancestors if conversation.id in right_ids),
            None,
        )

        left_messages = await self._load_ordered_messages(left.id)
        right_messages = await self._load_ordered_messages(right.id)

        shared: list[Message] = []
        divergence_index = 0
        for index, (left_message, right_message) in enumerate(
            zip(left_messages, right_messages, strict=False)
        ):
            if (
                left_message.role != right_message.role
                or left_message.content != right_message.content
            ):
                break
            shared.append(left_message)
            divergence_index = index + 1

        return ConversationCompareResponse(
            left_id=left.id,
            right_id=right.id,
            common_ancestor_id=common_ancestor.id if common_ancestor else None,
            shared_messages=[self._to_comparison_message(message) for message in shared],
            left_only=[
                self._to_comparison_message(message) for message in left_messages[divergence_index:]
            ],
            right_only=[
                self._to_comparison_message(message)
                for message in right_messages[divergence_index:]
            ],
            divergence_message_id=shared[-1].id if shared else None,
        )

    async def get_timeline(self, conversation: Conversation) -> ConversationTimelineResponse:
        events: list[TimelineEvent] = []
        user_ids: list[UUID] = []
        if conversation.created_by_id is not None:
            user_ids.append(conversation.created_by_id)
        user_ids.append(conversation.owner_id)

        participants_result = await self.db.execute(
            select(ConversationParticipant, User)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == conversation.id)
            .order_by(ConversationParticipant.joined_at.asc())
        )
        participants = list(participants_result.all())
        user_ids.extend(participant.user_id for participant, _ in participants)
        user_names = await self._load_user_names(user_ids)

        creator_name = (
            user_names.get(conversation.created_by_id)
            if conversation.created_by_id is not None
            else None
        )
        events.append(
            TimelineEvent(
                event_type="ConversationCreated",
                occurred_at=conversation.created_at,
                actor_id=conversation.created_by_id,
                actor_name=creator_name,
                summary=f"Conversation created: {conversation.title}",
                metadata={"title": conversation.title},
            )
        )

        if conversation.parent_conversation_id is not None:
            parent_result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation.parent_conversation_id)
            )
            parent = parent_result.scalar_one_or_none()
            events.append(
                TimelineEvent(
                    event_type="ConversationBranched",
                    occurred_at=conversation.created_at,
                    actor_id=conversation.created_by_id,
                    actor_name=creator_name,
                    summary=(
                        f"Branched as {conversation.branch_name or conversation.title}"
                        + (f" from {parent.title}" if parent is not None else "")
                    ),
                    metadata={
                        "parent_conversation_id": str(conversation.parent_conversation_id),
                        "branch_name": conversation.branch_name,
                        "branch_from_message_id": (
                            str(conversation.branch_from_message_id)
                            if conversation.branch_from_message_id
                            else None
                        ),
                    },
                )
            )

        for participant, user in participants:
            events.append(
                TimelineEvent(
                    event_type="ParticipantsAdded",
                    occurred_at=participant.joined_at,
                    actor_id=participant.user_id,
                    actor_name=user.name,
                    summary=f"{user.name} joined as {participant.role.value}",
                    metadata={
                        "user_id": str(participant.user_id),
                        "role": participant.role.value,
                    },
                )
            )

        if (
            conversation.created_by_id is not None
            and conversation.owner_id != conversation.created_by_id
        ):
            events.append(
                TimelineEvent(
                    event_type="OwnerChanged",
                    occurred_at=conversation.updated_at,
                    actor_id=conversation.owner_id,
                    actor_name=user_names.get(conversation.owner_id),
                    summary=(
                        f"Ownership is held by {user_names.get(conversation.owner_id, 'unknown')}"
                    ),
                    metadata={
                        "owner_id": str(conversation.owner_id),
                        "created_by_id": str(conversation.created_by_id),
                    },
                )
            )

        events.sort(key=lambda event: event.occurred_at)
        return ConversationTimelineResponse(conversation_id=conversation.id, events=events)

    async def get_stats(self, conversation: Conversation) -> ConversationStatsResponse:
        message_result = await self.db.execute(
            select(Message.role, func.count())
            .where(Message.conversation_id == conversation.id)
            .group_by(Message.role)
        )
        role_counts = {role: count for role, count in message_result.all()}
        message_count = sum(role_counts.values())
        assistant_messages = role_counts.get(MessageRole.ASSISTANT, 0)
        user_messages = role_counts.get(MessageRole.USER, 0)

        participant_result = await self.db.execute(
            select(func.count())
            .select_from(ConversationParticipant)
            .where(ConversationParticipant.conversation_id == conversation.id)
        )
        participants = int(participant_result.scalar_one())

        provider_result = await self.db.execute(
            select(AIRequest.provider)
            .where(AIRequest.conversation_id == conversation.id)
            .distinct()
            .order_by(AIRequest.provider.asc())
        )
        providers_used = list(provider_result.scalars().all())

        request_ids_result = await self.db.execute(
            select(AIRequest.id).where(AIRequest.conversation_id == conversation.id)
        )
        request_ids = list(request_ids_result.scalars().all())
        borrowed_requests = 0
        credits_used = Decimal("0")
        if request_ids:
            borrow_result = await self.db.execute(
                select(func.count()).where(BorrowRecord.request_id.in_(request_ids))
            )
            borrowed_requests = int(borrow_result.scalar_one())
            credits_result = await self.db.execute(
                select(func.coalesce(func.sum(AIRequest.estimated_cost), 0)).where(
                    AIRequest.conversation_id == conversation.id
                )
            )
            credits_used = Decimal(str(credits_result.scalar_one()))

        return ConversationStatsResponse(
            conversation_id=conversation.id,
            message_count=message_count,
            assistant_messages=assistant_messages,
            user_messages=user_messages,
            participants=participants,
            providers_used=providers_used,
            borrowed_requests=borrowed_requests,
            credits_used=format(credits_used, "f"),
            latest_activity=conversation.last_activity_at,
        )

    async def search(
        self,
        conversation: Conversation,
        query: str,
        *,
        context: int = 1,
    ) -> ConversationSearchResponse:
        cleaned = query.strip()
        if not cleaned:
            return ConversationSearchResponse(
                conversation_id=conversation.id,
                query=query,
                matches=[],
            )

        messages = await self._load_ordered_messages(conversation.id)
        matches: list[SearchMessageMatch] = []
        needle = cleaned.lower()
        for index, message in enumerate(messages):
            if needle not in message.content.lower():
                continue
            before_start = max(0, index - context)
            after_end = min(len(messages), index + context + 1)
            matches.append(
                SearchMessageMatch(
                    message=self._to_comparison_message(message),
                    context_before=[
                        self._to_comparison_message(item) for item in messages[before_start:index]
                    ],
                    context_after=[
                        self._to_comparison_message(item)
                        for item in messages[index + 1 : after_end]
                    ],
                )
            )
        return ConversationSearchResponse(
            conversation_id=conversation.id,
            query=query,
            matches=matches,
        )

    async def _find_root(self, conversation: Conversation) -> Conversation:
        cursor = conversation
        seen: set[UUID] = {conversation.id}
        while cursor.parent_conversation_id is not None:
            parent_result = await self.db.execute(
                select(Conversation).where(Conversation.id == cursor.parent_conversation_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None or parent.id in seen:
                break
            seen.add(parent.id)
            cursor = parent
        return cursor

    async def _load_descendants(
        self,
        root_id: UUID,
        workspace_id: UUID,
    ) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.id != root_id,
            )
        )
        all_conversations = list(result.scalars().all())
        by_parent: dict[UUID, list[Conversation]] = {}
        for conversation in all_conversations:
            if conversation.parent_conversation_id is None:
                continue
            by_parent.setdefault(conversation.parent_conversation_id, []).append(conversation)

        descendants: list[Conversation] = []
        stack = list(by_parent.get(root_id, []))
        while stack:
            current = stack.pop()
            descendants.append(current)
            stack.extend(by_parent.get(current.id, []))
        return descendants

    async def _ancestor_chain(self, conversation: Conversation) -> list[Conversation]:
        chain = [conversation]
        seen = {conversation.id}
        cursor = conversation
        while cursor.parent_conversation_id is not None:
            parent_result = await self.db.execute(
                select(Conversation).where(Conversation.id == cursor.parent_conversation_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None or parent.id in seen:
                break
            seen.add(parent.id)
            chain.append(parent)
            cursor = parent
        return chain

    async def _load_ordered_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(result.scalars().all())

    async def _load_user_names(self, user_ids: list[UUID]) -> dict[UUID, str]:
        unique_ids = list({user_id for user_id in user_ids if user_id is not None})
        if not unique_ids:
            return {}
        result = await self.db.execute(select(User).where(User.id.in_(unique_ids)))
        return {user.id: user.name for user in result.scalars().all()}

    async def _load_message_counts(self, conversation_ids: list[UUID]) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        result = await self.db.execute(
            select(Message.conversation_id, func.count())
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
        )
        return {conversation_id: count for conversation_id, count in result.all()}

    async def _load_participant_counts(self, conversation_ids: list[UUID]) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        result = await self.db.execute(
            select(ConversationParticipant.conversation_id, func.count())
            .where(ConversationParticipant.conversation_id.in_(conversation_ids))
            .group_by(ConversationParticipant.conversation_id)
        )
        return {conversation_id: count for conversation_id, count in result.all()}

    @staticmethod
    def _to_comparison_message(message: Message) -> ComparisonMessage:
        return ComparisonMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            author_id=message.author_id,
        )
