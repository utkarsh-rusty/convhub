"""Read-only branch visualization and comparison helpers."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.schemas import (
    BranchFamilyOverviewResponse,
    BranchManagerResponse,
    BranchTreeNode,
    BranchTreeResponse,
    CommitGraphEdge,
    CommitGraphNode,
    CommitGraphResponse,
    CommitSearchResponse,
    CommitSearchResult,
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
from app.models.conversation_commit import ConversationCommit
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User


class ConversationInsightsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_branch_tree(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> BranchTreeResponse:
        root_node = await self._build_branch_tree(conversation, viewer_user_id=viewer_user_id)
        return BranchTreeResponse(root=root_node)

    async def get_branch_manager(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> BranchManagerResponse:
        root_node = await self._build_branch_tree(conversation, viewer_user_id=viewer_user_id)
        totals = self._summarize_tree(root_node)
        return BranchManagerResponse(
            root=root_node,
            total_branches=totals["branches"],
            total_commits=totals["commits"],
            total_messages=totals["messages"],
            total_participants=totals["participants"],
        )

    async def get_commit_graph(self, conversation: Conversation) -> CommitGraphResponse:
        root = await self._find_root(conversation)
        descendants = await self._load_descendants(root.id, root.workspace_id)
        conversations = [root, *descendants]
        conversation_ids = [item.id for item in conversations]
        by_id = {item.id: item for item in conversations}

        commits_result = await self.db.execute(
            select(ConversationCommit, User)
            .join(User, User.id == ConversationCommit.created_by_id)
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .order_by(ConversationCommit.created_at.asc())
        )
        rows = list(commits_result.all())
        if not rows:
            return CommitGraphResponse()

        parent_hash_by_id: dict[UUID, str] = {commit.id: commit.commit_hash for commit, _ in rows}
        range_meta = await self._load_commit_range_summaries(rows)

        nodes: list[CommitGraphNode] = []
        edges: list[CommitGraphEdge] = []
        for commit, author in rows:
            conversation_row = by_id[commit.conversation_id]
            meta = range_meta.get(commit.id, {})
            parent_hash = None
            if commit.parent_commit_id is not None:
                parent_hash = parent_hash_by_id.get(commit.parent_commit_id)
            nodes.append(
                CommitGraphNode(
                    commit_hash=commit.commit_hash,
                    title=commit.title,
                    description=commit.description,
                    author_id=author.id,
                    author_name=author.name,
                    created_at=commit.created_at,
                    conversation_id=commit.conversation_id,
                    branch_name=conversation_row.branch_name,
                    conversation_title=conversation_row.title,
                    parent_commit_hash=parent_hash,
                    latest_message_id=commit.latest_message_id,
                    providers=meta.get("providers", []),
                    credits_used=meta.get("credits_used", "0"),
                    borrowed_requests=meta.get("borrowed_requests", 0),
                )
            )
            if parent_hash is not None:
                edges.append(CommitGraphEdge(source=parent_hash, target=commit.commit_hash))

        # Branch fork edges: first commit on a branch links visually from parent branch tip.
        for conversation_row in conversations:
            if conversation_row.parent_conversation_id is None:
                continue
            branch_commits = [
                commit for commit, _ in rows if commit.conversation_id == conversation_row.id
            ]
            if not branch_commits:
                continue
            first = min(branch_commits, key=lambda item: (item.created_at, item.id))
            parent_commits = [
                commit
                for commit, _ in rows
                if commit.conversation_id == conversation_row.parent_conversation_id
            ]
            if not parent_commits:
                continue
            parent_tip = max(parent_commits, key=lambda item: (item.created_at, item.id))
            if first.parent_commit_id is None:
                edges.append(
                    CommitGraphEdge(source=parent_tip.commit_hash, target=first.commit_hash)
                )

        # Deduplicate edges
        unique_edges = {(edge.source, edge.target): edge for edge in edges}
        return CommitGraphResponse(nodes=nodes, edges=list(unique_edges.values()))

    async def get_family_overview(self, conversation: Conversation) -> BranchFamilyOverviewResponse:
        root = await self._find_root(conversation)
        descendants = await self._load_descendants(root.id, root.workspace_id)
        conversations = [root, *descendants]
        conversation_ids = [item.id for item in conversations]

        message_counts = await self._load_message_counts(conversation_ids)
        participant_counts = await self._load_participant_counts(conversation_ids)
        commit_counts = await self._load_commit_counts(conversation_ids)

        ai_result = await self.db.execute(
            select(func.count()).where(AIRequest.conversation_id.in_(conversation_ids))
        )
        ai_request_count = int(ai_result.scalar_one())

        provider_result = await self.db.execute(
            select(AIRequest.provider)
            .where(AIRequest.conversation_id.in_(conversation_ids))
            .distinct()
            .order_by(AIRequest.provider.asc())
        )
        providers_used = list(provider_result.scalars().all())

        credits_result = await self.db.execute(
            select(func.coalesce(func.sum(AIRequest.estimated_cost), 0)).where(
                AIRequest.conversation_id.in_(conversation_ids)
            )
        )
        credits_used = Decimal(str(credits_result.scalar_one()))

        latest_activity = max(
            (item.last_activity_at for item in conversations),
            default=None,
        )
        unique_participants = sum(participant_counts.values())

        return BranchFamilyOverviewResponse(
            root_id=root.id,
            total_commits=sum(commit_counts.values()),
            total_branches=len(conversations),
            total_participants=unique_participants,
            total_messages=sum(message_counts.values()),
            ai_request_count=ai_request_count,
            latest_activity=latest_activity,
            providers_used=providers_used,
            credits_used=format(credits_used, "f"),
        )

    async def search_commits_advanced(
        self,
        conversation: Conversation,
        *,
        query: str = "",
        author: str = "",
        provider: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> CommitSearchResponse:
        root = await self._find_root(conversation)
        descendants = await self._load_descendants(root.id, root.workspace_id)
        conversations = [root, *descendants]
        by_id = {item.id: item for item in conversations}
        conversation_ids = list(by_id.keys())

        commits_result = await self.db.execute(
            select(ConversationCommit, User)
            .join(User, User.id == ConversationCommit.created_by_id)
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .order_by(ConversationCommit.created_at.desc())
        )
        rows = list(commits_result.all())
        range_meta = await self._load_commit_range_summaries(rows)

        needle = query.strip().lower()
        author_needle = author.strip().lower()
        provider_needle = provider.strip().lower()

        message_match_ids: set[UUID] = set()
        if needle:
            message_result = await self.db.execute(
                select(Message.id, Message.conversation_id, Message.content, Message.created_at)
                .where(Message.conversation_id.in_(conversation_ids))
                .order_by(Message.created_at.asc())
            )
            messages = list(message_result.all())
            for message_id, conversation_id, content, created_at in messages:
                if needle in content.lower():
                    message_match_ids.add(message_id)

        results: list[CommitSearchResult] = []
        for commit, user in rows:
            meta = range_meta.get(commit.id, {})
            providers = meta.get("providers", [])
            reasons: list[str] = []

            if author_needle and author_needle not in user.name.lower():
                continue
            if provider_needle and not any(provider_needle in item.lower() for item in providers):
                continue
            if date_from and commit.created_at.date().isoformat() < date_from:
                continue
            if date_to and commit.created_at.date().isoformat() > date_to:
                continue

            if needle:
                if needle in commit.title.lower():
                    reasons.append("title")
                if commit.description and needle in commit.description.lower():
                    reasons.append("description")
                if needle in user.name.lower():
                    reasons.append("author")
                if any(needle in item.lower() for item in providers):
                    reasons.append("provider")
                if commit.latest_message_id in message_match_ids:
                    reasons.append("message")
                # Also match messages in commit range by timestamp between parent and commit
                if not reasons:
                    continue
            else:
                reasons.append("filter")

            conversation_row = by_id[commit.conversation_id]
            results.append(
                CommitSearchResult(
                    commit_hash=commit.commit_hash,
                    title=commit.title,
                    description=commit.description,
                    author_name=user.name,
                    created_at=commit.created_at,
                    conversation_id=commit.conversation_id,
                    branch_name=conversation_row.branch_name,
                    latest_message_id=commit.latest_message_id,
                    providers=providers,
                    match_reason=",".join(reasons),
                )
            )

        return CommitSearchResponse(
            conversation_id=conversation.id,
            query=query,
            results=results,
        )

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
        from app.conversations.commits import ConversationCommitService

        commit_matches = await ConversationCommitService(self.db).search_commits(
            conversation.id,
            cleaned,
        )
        return ConversationSearchResponse(
            conversation_id=conversation.id,
            query=query,
            matches=matches,
            commit_matches=commit_matches,
        )

    async def _build_branch_tree(
        self,
        conversation: Conversation,
        *,
        viewer_user_id: UUID | None = None,
    ) -> BranchTreeNode:
        root = await self._find_root(conversation)
        descendants = await self._load_descendants(root.id, root.workspace_id)
        nodes = [root, *descendants]
        owner_names = await self._load_user_names([node.owner_id for node in nodes])
        message_counts = await self._load_message_counts([node.id for node in nodes])
        participant_counts = await self._load_participant_counts([node.id for node in nodes])
        commit_counts = await self._load_commit_counts([node.id for node in nodes])
        participant_membership = await self._load_participant_membership(
            [node.id for node in nodes],
            viewer_user_id,
        )
        status_map = await self._load_branch_status(nodes)

        node_map: dict[UUID, BranchTreeNode] = {}
        for node in nodes:
            status = status_map.get(node.id, {})
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
                commit_count=commit_counts.get(node.id, 0),
                commits_ahead=status.get("ahead", 0),
                commits_behind=status.get("behind", 0),
                common_ancestor_commit_hash=status.get("common_ancestor"),
                archived_at=node.archived_at,
                is_participant=participant_membership.get(node.id, False),
                is_owned_by_viewer=(viewer_user_id is not None and node.owner_id == viewer_user_id),
                created_at=node.created_at,
                children=[],
            )

        for node in nodes:
            parent_id = node.parent_conversation_id
            if parent_id is not None and parent_id in node_map and node.id != root.id:
                node_map[parent_id].children.append(node_map[node.id])

        for tree_node in node_map.values():
            tree_node.children.sort(key=lambda child: child.latest_activity_at, reverse=True)

        return node_map[root.id]

    @staticmethod
    def _summarize_tree(node: BranchTreeNode) -> dict[str, int]:
        totals = {
            "branches": 1,
            "commits": node.commit_count,
            "messages": node.message_count,
            "participants": node.participant_count,
        }
        for child in node.children:
            child_totals = ConversationInsightsService._summarize_tree(child)
            totals["branches"] += child_totals["branches"]
            totals["commits"] += child_totals["commits"]
            totals["messages"] += child_totals["messages"]
            totals["participants"] += child_totals["participants"]
        return totals

    async def _load_commit_counts(self, conversation_ids: list[UUID]) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        result = await self.db.execute(
            select(ConversationCommit.conversation_id, func.count())
            .where(ConversationCommit.conversation_id.in_(conversation_ids))
            .group_by(ConversationCommit.conversation_id)
        )
        return {conversation_id: count for conversation_id, count in result.all()}

    async def _load_participant_membership(
        self,
        conversation_ids: list[UUID],
        viewer_user_id: UUID | None,
    ) -> dict[UUID, bool]:
        if not conversation_ids or viewer_user_id is None:
            return {}
        result = await self.db.execute(
            select(ConversationParticipant.conversation_id).where(
                ConversationParticipant.conversation_id.in_(conversation_ids),
                ConversationParticipant.user_id == viewer_user_id,
            )
        )
        return {conversation_id: True for conversation_id in result.scalars().all()}

    async def _load_branch_status(
        self,
        conversations: list[Conversation],
    ) -> dict[UUID, dict[str, object]]:
        conversation_ids = [item.id for item in conversations]
        if not conversation_ids:
            return {}

        commits_result = await self.db.execute(
            select(ConversationCommit).where(
                ConversationCommit.conversation_id.in_(conversation_ids)
            )
        )
        commits = list(commits_result.scalars().all())
        commits_by_conversation: dict[UUID, list[ConversationCommit]] = {}
        for commit in commits:
            commits_by_conversation.setdefault(commit.conversation_id, []).append(commit)

        by_id = {item.id: item for item in conversations}
        status: dict[UUID, dict[str, object]] = {}
        for conversation in conversations:
            branch_commits = commits_by_conversation.get(conversation.id, [])
            ahead = len(branch_commits)
            behind = 0
            common_ancestor: str | None = None
            parent_id = conversation.parent_conversation_id
            if parent_id is not None and parent_id in by_id:
                parent = by_id[parent_id]
                parent_commits = commits_by_conversation.get(parent.id, [])
                behind = sum(
                    1 for commit in parent_commits if commit.created_at > conversation.created_at
                )
                if conversation.branch_from_message_id is not None:
                    for commit in sorted(
                        parent_commits,
                        key=lambda item: (item.created_at, item.id),
                        reverse=True,
                    ):
                        if commit.latest_message_id == conversation.branch_from_message_id:
                            common_ancestor = commit.commit_hash
                            break
                if common_ancestor is None and parent_commits:
                    tip = max(parent_commits, key=lambda item: (item.created_at, item.id))
                    if tip.created_at <= conversation.created_at:
                        common_ancestor = tip.commit_hash
            status[conversation.id] = {
                "ahead": ahead,
                "behind": behind,
                "common_ancestor": common_ancestor,
            }
        return status

    async def _load_commit_range_summaries(
        self,
        rows: list[tuple[ConversationCommit, User]],
    ) -> dict[UUID, dict[str, object]]:
        if not rows:
            return {}

        conversation_ids = list({commit.conversation_id for commit, _ in rows})
        messages_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        messages = list(messages_result.scalars().all())
        messages_by_conversation: dict[UUID, list[Message]] = {}
        for message in messages:
            messages_by_conversation.setdefault(message.conversation_id, []).append(message)

        commits_by_conversation: dict[UUID, list[ConversationCommit]] = {}
        for commit, _ in rows:
            commits_by_conversation.setdefault(commit.conversation_id, []).append(commit)

        summaries: dict[UUID, dict[str, object]] = {}
        for commit, _ in rows:
            conversation_messages = messages_by_conversation.get(commit.conversation_id, [])
            message_ids = [message.id for message in conversation_messages]
            if commit.latest_message_id not in message_ids:
                summaries[commit.id] = {
                    "providers": [],
                    "credits_used": "0",
                    "borrowed_requests": 0,
                }
                continue

            end_index = message_ids.index(commit.latest_message_id) + 1
            start_index = 0
            if commit.parent_commit_id is not None:
                siblings = commits_by_conversation.get(commit.conversation_id, [])
                parent = next(
                    (item for item in siblings if item.id == commit.parent_commit_id),
                    None,
                )
                if parent is not None and parent.latest_message_id in message_ids:
                    start_index = message_ids.index(parent.latest_message_id) + 1

            range_ids = message_ids[start_index:end_index]
            if not range_ids:
                summaries[commit.id] = {
                    "providers": [],
                    "credits_used": "0",
                    "borrowed_requests": 0,
                }
                continue

            request_result = await self.db.execute(
                select(AIRequest).where(
                    AIRequest.conversation_id == commit.conversation_id,
                    AIRequest.assistant_message_id.in_(range_ids),
                )
            )
            requests = list(request_result.scalars().all())
            providers: list[str] = []
            for request in requests:
                if request.provider not in providers:
                    providers.append(request.provider)
            credits = sum((request.estimated_cost or Decimal("0")) for request in requests)
            request_ids = [request.id for request in requests]
            borrowed_requests = 0
            if request_ids:
                borrow_result = await self.db.execute(
                    select(func.count()).where(BorrowRecord.request_id.in_(request_ids))
                )
                borrowed_requests = int(borrow_result.scalar_one())
            summaries[commit.id] = {
                "providers": providers,
                "credits_used": format(credits, "f"),
                "borrowed_requests": borrowed_requests,
            }
        return summaries

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
