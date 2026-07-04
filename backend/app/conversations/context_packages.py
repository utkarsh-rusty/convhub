"""Deterministic Context Package generation and retrieval."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.schemas import (
    ContextPackageExportResponse,
    ContextPackageListItem,
    ContextPackageResponse,
)
from app.models.ai_request import AIRequest
from app.models.borrow_record import BorrowRecord
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace


class ContextPackageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_for_commit(
        self,
        commit: ConversationCommit,
        conversation: Conversation,
        *,
        flush: bool = True,
    ) -> ContextPackage:
        """Build an immutable package for a commit. Caller owns the transaction."""
        existing = await self.db.execute(
            select(ContextPackage).where(ContextPackage.commit_id == commit.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Context package already exists for this commit",
            )

        workspace_result = await self.db.execute(
            select(Workspace).where(Workspace.id == conversation.workspace_id)
        )
        workspace = workspace_result.scalar_one()

        author_result = await self.db.execute(select(User).where(User.id == commit.created_by_id))
        author = author_result.scalar_one()

        participants_result = await self.db.execute(
            select(ConversationParticipant, User)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == conversation.id)
            .order_by(ConversationParticipant.joined_at.asc())
        )
        participants = [
            {
                "user_id": str(participant.user_id),
                "name": user.name,
                "role": participant.role.value,
            }
            for participant, user in participants_result.all()
        ]

        messages_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        messages = list(messages_result.scalars().all())
        message_ids = [message.id for message in messages]
        end_index = (
            message_ids.index(commit.latest_message_id) + 1
            if commit.latest_message_id in message_ids
            else len(messages)
        )
        start_index = 0
        if commit.parent_commit_id is not None:
            parent_result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == commit.parent_commit_id)
            )
            parent_commit = parent_result.scalar_one_or_none()
            if parent_commit is not None and parent_commit.latest_message_id in message_ids:
                start_index = message_ids.index(parent_commit.latest_message_id) + 1

        range_messages = messages[:end_index]
        introduced_messages = messages[start_index:end_index]

        role_counts = {
            MessageRole.USER: 0,
            MessageRole.ASSISTANT: 0,
            MessageRole.SYSTEM: 0,
        }
        for message in range_messages:
            role_counts[message.role] = role_counts.get(message.role, 0) + 1

        range_ids = [message.id for message in range_messages]
        requests: list[AIRequest] = []
        if range_ids:
            request_result = await self.db.execute(
                select(AIRequest).where(
                    AIRequest.conversation_id == conversation.id,
                    AIRequest.assistant_message_id.in_(range_ids),
                )
            )
            requests = list(request_result.scalars().all())

        providers: list[str] = []
        models: list[str] = []
        for request in requests:
            if request.provider not in providers:
                providers.append(request.provider)
            if request.model not in models:
                models.append(request.model)

        credits_used = sum((request.estimated_cost or Decimal("0")) for request in requests)
        request_ids = [request.id for request in requests]
        borrow_rows: list[dict[str, Any]] = []
        if request_ids:
            borrow_result = await self.db.execute(
                select(BorrowRecord, User)
                .join(User, User.id == BorrowRecord.lender_user_id)
                .where(BorrowRecord.request_id.in_(request_ids))
            )
            for record, lender in borrow_result.all():
                borrow_rows.append(
                    {
                        "request_id": str(record.request_id),
                        "lender_user_id": str(record.lender_user_id),
                        "lender_name": lender.name,
                        "borrower_user_id": str(record.borrower_user_id),
                    }
                )

        parent_conversation_title: str | None = None
        if conversation.parent_conversation_id is not None:
            parent_conv_result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation.parent_conversation_id)
            )
            parent_conversation = parent_conv_result.scalar_one_or_none()
            if parent_conversation is not None:
                parent_conversation_title = parent_conversation.title

        parent_commit_hash: str | None = None
        if commit.parent_commit_id is not None:
            parent_hash_result = await self.db.execute(
                select(ConversationCommit.commit_hash).where(
                    ConversationCommit.id == commit.parent_commit_id
                )
            )
            parent_commit_hash = parent_hash_result.scalar_one_or_none()

        snapshot_messages = [
            {
                "id": str(message.id),
                "role": message.role.value,
                "content": message.content,
                "author_id": str(message.author_id) if message.author_id else None,
                "created_at": message.created_at.isoformat(),
            }
            for message in introduced_messages
        ]

        metadata_json: dict[str, Any] = {
            "workspace": {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
            },
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "branch_name": conversation.branch_name,
                "parent_conversation_id": (
                    str(conversation.parent_conversation_id)
                    if conversation.parent_conversation_id
                    else None
                ),
                "parent_conversation_title": parent_conversation_title,
                "branch_from_message_id": (
                    str(conversation.branch_from_message_id)
                    if conversation.branch_from_message_id
                    else None
                ),
                "owner_id": str(conversation.owner_id),
                "created_at": conversation.created_at.isoformat(),
                "last_activity_at": conversation.last_activity_at.isoformat(),
            },
            "commit": {
                "id": str(commit.id),
                "commit_hash": commit.commit_hash,
                "title": commit.title,
                "description": commit.description,
                "parent_commit_id": (
                    str(commit.parent_commit_id) if commit.parent_commit_id else None
                ),
                "parent_commit_hash": parent_commit_hash,
                "latest_message_id": str(commit.latest_message_id),
                "created_by_id": str(author.id),
                "created_by_name": author.name,
                "created_at": commit.created_at.isoformat(),
            },
            "participants": participants,
            "providers_used": providers,
            "models_used": models,
            "borrow_records": borrow_rows,
            "generated_at": datetime.now(UTC).isoformat(),
            "package_version": 1,
        }

        summary_json: dict[str, Any] = {
            "title": commit.title,
            "description": commit.description,
            "branch_name": conversation.branch_name,
            "conversation_title": conversation.title,
            "author_name": author.name,
            "message_preview": [
                {
                    "role": message.role.value,
                    "content": message.content[:240],
                }
                for message in introduced_messages[:5]
            ],
            "architecture_notes": [],
            "decisions": [],
            "todos": [],
            "conversation_snapshot": snapshot_messages,
        }

        statistics_json: dict[str, Any] = {
            "message_count": len(range_messages),
            "introduced_message_count": len(introduced_messages),
            "user_messages": role_counts.get(MessageRole.USER, 0),
            "assistant_messages": role_counts.get(MessageRole.ASSISTANT, 0),
            "system_messages": role_counts.get(MessageRole.SYSTEM, 0),
            "participant_count": len(participants),
            "ai_request_count": len(requests),
            "providers_used": providers,
            "models_used": models,
            "credits_used": format(credits_used, "f"),
            "borrowed_requests": len(borrow_rows),
            "borrow_lenders": sorted({row["lender_name"] for row in borrow_rows}),
        }

        keywords = self._build_keywords(
            commit_title=commit.title,
            commit_description=commit.description,
            conversation_title=conversation.title,
            branch_name=conversation.branch_name,
            author_name=author.name,
            participant_names=[item["name"] for item in participants],
            providers=providers,
            models=models,
        )

        package = ContextPackage(
            id=uuid4(),
            commit_id=commit.id,
            conversation_id=conversation.id,
            version=1,
            status="generated",
            generated_at=datetime.now(UTC),
            metadata_json=metadata_json,
            summary_json=summary_json,
            statistics_json=statistics_json,
            search_keywords_json=keywords,
        )
        self.db.add(package)
        if flush:
            await self.db.flush()
        return package

    async def get_by_id(self, package_id: UUID, workspace_id: UUID) -> ContextPackageResponse:
        package = await self._load_package(package_id)
        await self._assert_workspace(package.conversation_id, workspace_id)
        return self._to_response(package)

    async def get_by_commit_id(self, commit_id: UUID, workspace_id: UUID) -> ContextPackageResponse:
        result = await self.db.execute(
            select(ContextPackage).where(ContextPackage.commit_id == commit_id)
        )
        package = result.scalar_one_or_none()
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context package not found",
            )
        await self._assert_workspace(package.conversation_id, workspace_id)
        return self._to_response(package)

    async def get_by_commit_ref(
        self, commit_ref: str, workspace_id: UUID
    ) -> ContextPackageResponse:
        commit = await self._resolve_commit(commit_ref)
        return await self.get_by_commit_id(commit.id, workspace_id)

    async def list_for_conversation(
        self, conversation_id: UUID, workspace_id: UUID
    ) -> list[ContextPackageListItem]:
        await self._assert_workspace(conversation_id, workspace_id)
        result = await self.db.execute(
            select(ContextPackage, ConversationCommit)
            .join(ConversationCommit, ConversationCommit.id == ContextPackage.commit_id)
            .where(ContextPackage.conversation_id == conversation_id)
            .order_by(ContextPackage.generated_at.desc())
        )
        return [
            ContextPackageListItem(
                id=package.id,
                commit_id=package.commit_id,
                commit_hash=commit.commit_hash,
                commit_title=commit.title,
                conversation_id=package.conversation_id,
                version=package.version,
                status=package.status,
                generated_at=package.generated_at,
            )
            for package, commit in result.all()
        ]

    async def export_by_id(
        self, package_id: UUID, workspace_id: UUID
    ) -> ContextPackageExportResponse:
        package = await self._load_package(package_id)
        await self._assert_workspace(package.conversation_id, workspace_id)
        return ContextPackageExportResponse(
            id=package.id,
            commit_id=package.commit_id,
            conversation_id=package.conversation_id,
            version=package.version,
            status=package.status,
            generated_at=package.generated_at,
            metadata=package.metadata_json,
            summary=package.summary_json,
            statistics=package.statistics_json,
            search_keywords=package.search_keywords_json,
        )

    async def _load_package(self, package_id: UUID) -> ContextPackage:
        result = await self.db.execute(
            select(ContextPackage).where(ContextPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context package not found",
            )
        return package

    async def _resolve_commit(self, commit_ref: str) -> ConversationCommit:
        try:
            commit_id = UUID(commit_ref)
            result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.id == commit_id)
            )
        except ValueError:
            result = await self.db.execute(
                select(ConversationCommit).where(ConversationCommit.commit_hash == commit_ref)
            )
        commit = result.scalar_one_or_none()
        if commit is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commit not found",
            )
        return commit

    async def _assert_workspace(self, conversation_id: UUID, workspace_id: UUID) -> None:
        result = await self.db.execute(
            select(Conversation.id).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Context package not found",
            )

    @staticmethod
    def _to_response(package: ContextPackage) -> ContextPackageResponse:
        return ContextPackageResponse(
            id=package.id,
            commit_id=package.commit_id,
            conversation_id=package.conversation_id,
            version=package.version,
            status=package.status,
            generated_at=package.generated_at,
            metadata=package.metadata_json,
            summary=package.summary_json,
            statistics=package.statistics_json,
            search_keywords=package.search_keywords_json,
        )

    @staticmethod
    def _build_keywords(
        *,
        commit_title: str,
        commit_description: str | None,
        conversation_title: str,
        branch_name: str | None,
        author_name: str,
        participant_names: list[str],
        providers: list[str],
        models: list[str],
    ) -> list[str]:
        tokens: list[str] = []
        for value in [
            commit_title,
            commit_description or "",
            conversation_title,
            branch_name or "",
            author_name,
            *participant_names,
            *providers,
            *models,
        ]:
            tokens.extend(re.findall(r"[a-zA-Z0-9_]{3,}", value.lower()))
        # Deterministic unique order
        seen: set[str] = set()
        keywords: list[str] = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                keywords.append(token)
        return keywords[:50]
