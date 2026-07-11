from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.branch_memory import BranchMemory
from app.models.branch_sync_record import BranchSyncRecord
from app.models.context_package import ContextPackage
from app.models.conversation import Conversation
from app.models.conversation_commit import ConversationCommit
from app.models.conversation_participant import ConversationParticipant
from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.enums import BranchSyncType, DeveloperWorkspaceSessionStatus
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.models.repository_memory import RepositoryMemory
from app.models.user import User
from app.models.workspace import Workspace
from app.repository_memory.schemas import (
    RepositoryMemoryExportResponse,
    RepositoryMemoryJsonExportResponse,
    RepositoryMemoryResponse,
)

logger = logging.getLogger(__name__)

ACTIVE_SESSION_STATUSES = (
    DeveloperWorkspaceSessionStatus.ACTIVE,
    DeveloperWorkspaceSessionStatus.IDLE,
    DeveloperWorkspaceSessionStatus.DISCONNECTED,
)

RECENT_COMMITS_LIMIT = 10
RECENT_PACKAGES_LIMIT = 10
BRANCH_HISTORY_LIMIT = 20


class RepositoryMemoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_repository_memory(
        self,
        repository_branch_id: UUID,
        *,
        commit: bool = True,
    ) -> RepositoryMemory:
        graph = await self._load_branch_graph(repository_branch_id)
        payload = await self._build_payload(graph)
        markdown = self._render_markdown(payload)

        result = await self.db.execute(
            select(RepositoryMemory)
            .options(noload("*"))
            .where(RepositoryMemory.repository_branch_id == repository_branch_id)
        )
        memory = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if memory is None:
            memory = RepositoryMemory(
                repository_branch_id=repository_branch_id,
                memory_version=1,
            )
            self.db.add(memory)
        else:
            memory.memory_version += 1

        memory.latest_commit_id = (
            UUID(payload["latest_commit"]["id"])
            if payload["latest_commit"] is not None
            else None
        )
        memory.latest_context_package_id = (
            UUID(payload["latest_context_package"]["id"])
            if payload["latest_context_package"] is not None
            else None
        )
        memory.latest_workspace_session_id = (
            UUID(payload["active_developer"]["session_id"])
            if payload["active_developer"] is not None
            else None
        )
        memory.generated_at = now
        memory.markdown_content = markdown
        memory.json_content = payload

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        return memory

    async def rebuild_for_branch_id(self, repository_branch_id: UUID) -> None:
        """Best-effort regeneration used by pipeline hooks."""
        try:
            await self.build_repository_memory(repository_branch_id, commit=True)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to rebuild repository memory for branch %s",
                repository_branch_id,
            )
            await self.db.rollback()

    async def rebuild_for_conversation(self, conversation: Conversation) -> None:
        repository_id = conversation.repository_id
        if repository_id is None:
            return
        branch = await self._resolve_default_branch(repository_id)
        if branch is None:
            return
        await self.rebuild_for_branch_id(branch.id)

    async def get_memory(self, branch: RepositoryBranch) -> RepositoryMemoryResponse:
        memory = await self._load_or_build(branch.id)
        return await self._to_response(memory, branch)

    async def export_markdown(self, branch: RepositoryBranch) -> RepositoryMemoryExportResponse:
        memory = await self._load_or_build(branch.id)
        return RepositoryMemoryExportResponse(
            filename=f"repository-memory-{branch.name}.md",
            content=memory.markdown_content,
            content_type="text/markdown",
        )

    async def export_json(self, branch: RepositoryBranch) -> RepositoryMemoryJsonExportResponse:
        memory = await self._load_or_build(branch.id)
        return RepositoryMemoryJsonExportResponse(
            filename=f"repository-memory-{branch.name}.json",
            content=memory.json_content,
        )

    async def _load_or_build(self, repository_branch_id: UUID) -> RepositoryMemory:
        result = await self.db.execute(
            select(RepositoryMemory)
            .options(noload("*"))
            .where(RepositoryMemory.repository_branch_id == repository_branch_id)
        )
        memory = result.scalar_one_or_none()
        if memory is not None:
            return memory
        return await self.build_repository_memory(repository_branch_id)

    async def _load_branch_graph(self, repository_branch_id: UUID) -> dict[str, Any]:
        row = (
            await self.db.execute(
                select(
                    RepositoryBranch.id,
                    RepositoryBranch.name,
                    RepositoryBranch.is_default,
                    Repository.id.label("repository_id"),
                    Repository.name.label("repository_name_display"),
                    Repository.owner,
                    Repository.repository_name,
                    Repository.remote_url,
                    Repository.provider,
                    Project.id.label("project_id"),
                    Project.name.label("project_name"),
                    Workspace.id.label("workspace_id"),
                    Workspace.name.label("workspace_name"),
                    Workspace.slug.label("workspace_slug"),
                )
                .join(Repository, Repository.id == RepositoryBranch.repository_id)
                .join(Project, Project.id == Repository.project_id)
                .join(Workspace, Workspace.id == Repository.workspace_id)
                .where(RepositoryBranch.id == repository_branch_id)
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository branch not found",
            )
        return {
            "branch_id": row.id,
            "branch_name": row.name,
            "branch_is_default": row.is_default,
            "repository_id": row.repository_id,
            "repository_name": row.repository_name_display,
            "repository_owner": row.owner,
            "repository_repository_name": row.repository_name,
            "repository_remote_url": row.remote_url,
            "repository_provider": row.provider,
            "project_id": row.project_id,
            "project_name": row.project_name,
            "workspace_id": row.workspace_id,
            "workspace_name": row.workspace_name,
            "workspace_slug": row.workspace_slug,
        }

    async def _resolve_default_branch(self, repository_id: UUID) -> RepositoryBranch | None:
        result = await self.db.execute(
            select(RepositoryBranch.id)
            .where(
                RepositoryBranch.repository_id == repository_id,
                RepositoryBranch.is_active.is_(True),
            )
            .order_by(RepositoryBranch.is_default.desc(), RepositoryBranch.created_at.asc())
        )
        branch_id = result.scalars().first()
        if branch_id is None:
            return None
        # Return a lightweight instance only used for .id access by callers.
        branch = RepositoryBranch(id=branch_id)
        return branch

    async def _build_payload(self, graph: dict[str, Any]) -> dict[str, Any]:
        branch_id = graph["branch_id"]
        memory_row = (
            await self.db.execute(
                select(
                    BranchMemory.id,
                    BranchMemory.latest_sync_record_id,
                    BranchMemory.current_sync_version,
                    BranchMemory.memory_version,
                )
                .where(BranchMemory.repository_branch_id == branch_id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()

        latest_record = None
        if memory_row is not None and memory_row.latest_sync_record_id is not None:
            latest_record = (
                await self.db.execute(
                    select(
                        BranchSyncRecord.id,
                        BranchSyncRecord.conversation_id,
                        BranchSyncRecord.commit_id,
                        BranchSyncRecord.context_package_id,
                        BranchSyncRecord.sync_type,
                    ).where(BranchSyncRecord.id == memory_row.latest_sync_record_id)
                )
            ).one_or_none()

        detached = (
            latest_record is not None
            and latest_record.sync_type == BranchSyncType.DETACH_REPOSITORY
        )

        conversation_id = None
        conversation_title = None
        conversation_branch_name = None
        conversation_owner = None
        if latest_record is not None and latest_record.conversation_id is not None and not detached:
            conversation_id = latest_record.conversation_id
            conversation_row = (
                await self.db.execute(
                    select(
                        Conversation.id,
                        Conversation.title,
                        Conversation.branch_name,
                        Conversation.owner_id,
                    ).where(Conversation.id == conversation_id)
                )
            ).one_or_none()
            if conversation_row is not None:
                conversation_title = conversation_row.title
                conversation_branch_name = conversation_row.branch_name
                conversation_owner = (
                    await self.db.execute(
                        select(User.name).where(User.id == conversation_row.owner_id)
                    )
                ).scalar_one_or_none()

        latest_commit = None
        if latest_record is not None and latest_record.commit_id is not None and not detached:
            commit_row = (
                await self.db.execute(
                    select(
                        ConversationCommit.id,
                        ConversationCommit.commit_hash,
                        ConversationCommit.title,
                        ConversationCommit.description,
                        ConversationCommit.created_at,
                    ).where(ConversationCommit.id == latest_record.commit_id)
                )
            ).one_or_none()
            if commit_row is not None:
                latest_commit = {
                    "id": str(commit_row.id),
                    "commit_hash": commit_row.commit_hash,
                    "title": commit_row.title,
                    "description": commit_row.description,
                    "created_at": commit_row.created_at.isoformat(),
                }

        latest_package = None
        architecture_notes: list[Any] = []
        decisions: list[Any] = []
        todos: list[Any] = []
        if (
            latest_record is not None
            and latest_record.context_package_id is not None
            and not detached
        ):
            package_row = (
                await self.db.execute(
                    select(
                        ContextPackage.id,
                        ContextPackage.version,
                        ContextPackage.generated_at,
                        ContextPackage.status,
                        ContextPackage.summary_json,
                    ).where(ContextPackage.id == latest_record.context_package_id)
                )
            ).one_or_none()
            if package_row is not None:
                status_value = package_row.status
                if hasattr(status_value, "value"):
                    status_value = status_value.value
                latest_package = {
                    "id": str(package_row.id),
                    "version": package_row.version,
                    "generated_at": package_row.generated_at.isoformat(),
                    "status": status_value,
                }
                summary = package_row.summary_json or {}
                architecture_notes = list(summary.get("architecture_notes") or [])
                decisions = list(summary.get("decisions") or [])
                todos = list(summary.get("todos") or [])

        participants = await self._load_participants(conversation_id)
        active_developer = await self._load_active_developer(branch_id)
        recent_commits = await self._load_recent_commits(conversation_id)
        branch_history = await self._load_branch_history(
            memory_row.id if memory_row is not None else None
        )
        package_refs = await self._load_package_refs(conversation_id)

        provider = graph["repository_provider"]
        provider_value = provider.value if hasattr(provider, "value") else provider

        return {
            "repository": {
                "id": str(graph["repository_id"]),
                "name": graph["repository_name"],
                "owner": graph["repository_owner"],
                "repository_name": graph["repository_repository_name"],
                "remote_url": graph["repository_remote_url"],
                "provider": provider_value,
            },
            "project": {
                "id": str(graph["project_id"]),
                "name": graph["project_name"],
            },
            "workspace": {
                "id": str(graph["workspace_id"]),
                "name": graph["workspace_name"],
                "slug": graph["workspace_slug"],
            },
            "active_conversation": (
                None
                if conversation_id is None or detached
                else {
                    "id": str(conversation_id),
                    "title": conversation_title,
                    "owner": conversation_owner,
                    "branch_name": conversation_branch_name,
                }
            ),
            "repository_branch": {
                "id": str(branch_id),
                "name": graph["branch_name"],
                "is_default": graph["branch_is_default"],
                "sync_version": memory_row.current_sync_version if memory_row is not None else 0,
                "memory_version": memory_row.memory_version if memory_row is not None else 0,
            },
            "latest_commit": latest_commit,
            "latest_context_package": latest_package,
            "participants": participants,
            "active_developer": active_developer,
            "architecture_notes": architecture_notes,
            "decisions": decisions,
            "todos": todos,
            "recent_commits": recent_commits,
            "branch_history": branch_history,
            "context_package_references": package_refs,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    async def _load_participants(self, conversation_id: UUID | None) -> list[dict[str, Any]]:
        if conversation_id is None:
            return []
        result = await self.db.execute(
            select(
                ConversationParticipant.user_id,
                ConversationParticipant.role,
                User.name,
                User.email,
            )
            .join(User, User.id == ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == conversation_id)
            .order_by(ConversationParticipant.joined_at.asc())
        )
        return [
            {
                "user_id": str(row.user_id),
                "name": row.name,
                "email": row.email,
                "role": row.role.value if hasattr(row.role, "value") else row.role,
            }
            for row in result.all()
        ]

    async def _load_active_developer(
        self,
        repository_branch_id: UUID,
    ) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(
                DeveloperWorkspaceSession.id,
                DeveloperWorkspaceSession.user_id,
                DeveloperWorkspaceSession.client_name,
                DeveloperWorkspaceSession.client_version,
                DeveloperWorkspaceSession.platform,
                DeveloperWorkspaceSession.status,
                DeveloperWorkspaceSession.started_at,
                DeveloperWorkspaceSession.last_heartbeat_at,
                User.name,
            )
            .join(User, User.id == DeveloperWorkspaceSession.user_id)
            .where(
                DeveloperWorkspaceSession.repository_branch_id == repository_branch_id,
                DeveloperWorkspaceSession.status.in_(ACTIVE_SESSION_STATUSES),
            )
            .order_by(DeveloperWorkspaceSession.last_heartbeat_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return {
            "session_id": str(row.id),
            "user_id": str(row.user_id),
            "user_name": row.name,
            "client_name": row.client_name,
            "client_version": row.client_version,
            "platform": row.platform,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "started_at": row.started_at.isoformat(),
            "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
        }

    async def _load_recent_commits(
        self,
        conversation_id: UUID | None,
    ) -> list[dict[str, Any]]:
        if conversation_id is None:
            return []
        result = await self.db.execute(
            select(
                ConversationCommit.id,
                ConversationCommit.commit_hash,
                ConversationCommit.title,
                ConversationCommit.created_at,
                User.name,
            )
            .join(User, User.id == ConversationCommit.created_by_id)
            .where(ConversationCommit.conversation_id == conversation_id)
            .order_by(ConversationCommit.created_at.desc(), ConversationCommit.id.desc())
            .limit(RECENT_COMMITS_LIMIT)
        )
        return [
            {
                "id": str(row.id),
                "commit_hash": row.commit_hash,
                "title": row.title,
                "created_by": row.name,
                "created_at": row.created_at.isoformat(),
            }
            for row in result.all()
        ]

    async def _load_branch_history(
        self,
        branch_memory_id: UUID | None,
    ) -> list[dict[str, Any]]:
        if branch_memory_id is None:
            return []
        result = await self.db.execute(
            select(
                BranchSyncRecord.id,
                BranchSyncRecord.sync_type,
                BranchSyncRecord.sync_version,
                BranchSyncRecord.notes,
                BranchSyncRecord.created_at,
            )
            .where(BranchSyncRecord.branch_memory_id == branch_memory_id)
            .order_by(BranchSyncRecord.sync_version.desc(), BranchSyncRecord.created_at.desc())
            .limit(BRANCH_HISTORY_LIMIT)
        )
        return [
            {
                "id": str(row.id),
                "sync_type": (
                    row.sync_type.value if hasattr(row.sync_type, "value") else row.sync_type
                ),
                "sync_version": row.sync_version,
                "notes": row.notes,
                "created_at": row.created_at.isoformat(),
            }
            for row in result.all()
        ]

    async def _load_package_refs(
        self,
        conversation_id: UUID | None,
    ) -> list[dict[str, Any]]:
        if conversation_id is None:
            return []
        result = await self.db.execute(
            select(
                ContextPackage.id,
                ContextPackage.version,
                ContextPackage.commit_id,
                ContextPackage.generated_at,
                ConversationCommit.commit_hash,
            )
            .join(ConversationCommit, ConversationCommit.id == ContextPackage.commit_id)
            .where(ContextPackage.conversation_id == conversation_id)
            .order_by(ContextPackage.generated_at.desc())
            .limit(RECENT_PACKAGES_LIMIT)
        )
        return [
            {
                "id": str(row.id),
                "version": row.version,
                "commit_id": str(row.commit_id),
                "commit_hash": row.commit_hash,
                "generated_at": row.generated_at.isoformat(),
            }
            for row in result.all()
        ]

    def _render_markdown(self, payload: dict[str, Any]) -> str:
        repo = payload["repository"]
        project = payload["project"]
        workspace = payload["workspace"]
        branch = payload["repository_branch"]
        conversation = payload["active_conversation"]
        latest_commit = payload["latest_commit"]
        latest_package = payload["latest_context_package"]
        participants = payload["participants"]
        active_developer = payload["active_developer"]
        architecture_notes = payload["architecture_notes"]
        decisions = payload["decisions"]
        todos = payload["todos"]
        recent_commits = payload["recent_commits"]
        branch_history = payload["branch_history"]
        packages = payload["context_package_references"]

        lines: list[str] = [
            "# Repository",
            "",
            f"- name: {repo['name']}",
            f"- project: {project['name']}",
            f"- workspace: {workspace['name']}",
            "",
            "# Active Conversation",
            "",
        ]
        if conversation is None:
            lines.append("- linked conversation: None")
            lines.append("- conversation owner: None")
        else:
            lines.append(f"- linked conversation: {conversation['title']}")
            lines.append(f"- conversation owner: {conversation['owner'] or 'Unknown'}")

        lines.extend(
            [
                "",
                "# Repository Branch",
                "",
                f"- branch: {branch['name']}",
                f"- sync version: {branch['sync_version']}",
                f"- memory version: {branch['memory_version']}",
                "",
                "# Latest Commit",
                "",
            ]
        )
        if latest_commit is None:
            lines.append("- latest commit: Not Available Yet")
        else:
            lines.append(f"- latest commit: #{latest_commit['commit_hash']}")
            lines.append(f"- commit message: {latest_commit['title']}")
            lines.append(f"- timestamp: {latest_commit['created_at']}")

        lines.extend(["", "# Latest Context Package", ""])
        if latest_package is None:
            lines.append("- package id: Not Available Yet")
        else:
            lines.append(f"- package id: {latest_package['id']}")
            lines.append(f"- timestamp: {latest_package['generated_at']}")

        lines.extend(["", "# Participants", ""])
        if not participants:
            lines.append("No coding participants.")
        else:
            for item in participants:
                lines.append(f"- {item['name']} ({item['role']})")

        lines.extend(["", "# Active Developer", ""])
        if active_developer is None:
            lines.append("No active workspace session.")
        else:
            client = active_developer.get("client_name") or "unknown"
            lines.append(
                f"- {active_developer['user_name']} via {client} "
                f"({active_developer['status']})"
            )

        lines.extend(["", "# Architecture Notes", ""])
        if not architecture_notes:
            lines.append("Not documented.")
        else:
            for note in architecture_notes:
                lines.append(f"- {note}")

        lines.extend(["", "# Decisions", ""])
        if not decisions:
            lines.append("No recorded decisions.")
        else:
            for decision in decisions:
                lines.append(f"- {decision}")

        lines.extend(["", "# Current TODOs", ""])
        if not todos:
            lines.append("No pending TODOs.")
        else:
            for todo in todos:
                lines.append(f"- {todo}")

        lines.extend(["", "# Recent Commits", ""])
        if not recent_commits:
            lines.append("No commits yet.")
        else:
            for commit in recent_commits:
                lines.append(
                    f"- #{commit['commit_hash']} {commit['title']} "
                    f"({commit['created_by']}, {commit['created_at']})"
                )

        lines.extend(["", "# Branch History", ""])
        if not branch_history:
            lines.append("No branch history.")
        else:
            for item in branch_history:
                note = f" — {item['notes']}" if item.get("notes") else ""
                lines.append(
                    f"- v{item['sync_version']} {item['sync_type']} "
                    f"({item['created_at']}){note}"
                )

        lines.extend(["", "# Context Package References", ""])
        if not packages:
            lines.append("No context packages.")
        else:
            for package in packages:
                lines.append(
                    f"- {package['id']} (v{package['version']}, "
                    f"#{package['commit_hash']}, {package['generated_at']})"
                )

        lines.append("")
        return "\n".join(lines)

    async def _to_response(
        self,
        memory: RepositoryMemory,
        branch: RepositoryBranch,
    ) -> RepositoryMemoryResponse:
        commit_hash = None
        package_version = None
        if memory.latest_commit_id is not None:
            commit_hash = (
                await self.db.execute(
                    select(ConversationCommit.commit_hash).where(
                        ConversationCommit.id == memory.latest_commit_id
                    )
                )
            ).scalar_one_or_none()
        if memory.latest_context_package_id is not None:
            package_version = (
                await self.db.execute(
                    select(ContextPackage.version).where(
                        ContextPackage.id == memory.latest_context_package_id
                    )
                )
            ).scalar_one_or_none()

        return RepositoryMemoryResponse(
            id=memory.id,
            repository_branch_id=memory.repository_branch_id,
            repository_id=branch.repository_id,
            repository_branch_name=branch.name,
            memory_version=memory.memory_version,
            latest_commit_id=memory.latest_commit_id,
            latest_commit_hash=commit_hash,
            latest_context_package_id=memory.latest_context_package_id,
            latest_context_package_version=package_version,
            latest_workspace_session_id=memory.latest_workspace_session_id,
            generated_at=memory.generated_at,
            markdown_content=memory.markdown_content,
            json_content=memory.json_content,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )
