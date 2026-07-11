from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.developer_workspace_session import DeveloperWorkspaceSession
from app.models.enums import DeveloperWorkspaceSessionStatus
from app.models.external_ai_session import ExternalAISession
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_branch import RepositoryBranch
from app.models.transcript_snapshot import TranscriptSnapshot
from app.models.user import User
from app.models.workspace import Workspace
from app.pull_packages.schemas import (
    PullPackageExportResponse,
    PullPackageJsonExportResponse,
    PullPackageResponse,
)
from app.repository_memory.service import RepositoryMemoryService
from app.sync.service import SyncService

ACTIVE_SESSION_STATUSES = (
    DeveloperWorkspaceSessionStatus.ACTIVE,
    DeveloperWorkspaceSessionStatus.IDLE,
    DeveloperWorkspaceSessionStatus.DISCONNECTED,
)


class PullPackageService:
    """Compose existing ConvHub artifacts into a downloadable Pull Package."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_pull_package(self, repository_branch_id: UUID) -> dict[str, Any]:
        branch, repository = await self._load_branch_and_repository(repository_branch_id)
        graph = await self._load_metadata(branch, repository)

        memory_response = await RepositoryMemoryService(self.db).get_memory(branch)
        sync_status = await SyncService(self.db).get_status(branch, repository)
        transcript = await self._load_latest_transcript_snapshot(repository_branch_id)
        active_developer = await self._load_active_developer(repository_branch_id)

        repository_memory = {
            "id": str(memory_response.id),
            "memory_version": memory_response.memory_version,
            "generated_at": memory_response.generated_at.isoformat(),
            "latest_commit_id": (
                str(memory_response.latest_commit_id)
                if memory_response.latest_commit_id is not None
                else None
            ),
            "latest_commit_hash": memory_response.latest_commit_hash,
            "latest_context_package_id": (
                str(memory_response.latest_context_package_id)
                if memory_response.latest_context_package_id is not None
                else None
            ),
            "latest_context_package_version": memory_response.latest_context_package_version,
            "markdown_content": memory_response.markdown_content,
            "json_content": memory_response.json_content,
        }

        latest_commit = None
        if sync_status.latest_commit is not None:
            commit = sync_status.latest_commit
            latest_commit = {
                "id": str(commit.id),
                "commit_hash": commit.commit_hash,
                "title": commit.title,
                "created_at": commit.created_at.isoformat(),
            }

        latest_context_package = None
        if sync_status.latest_context_package is not None:
            package = sync_status.latest_context_package
            latest_context_package = {
                "id": str(package.id),
                "commit_id": str(package.commit_id),
                "commit_hash": package.commit_hash,
                "version": package.version,
                "generated_at": package.generated_at.isoformat(),
            }

        sync = {
            "sync_version": sync_status.sync_version,
            "sync_state": (
                sync_status.sync_state.value
                if hasattr(sync_status.sync_state, "value")
                else sync_status.sync_state
            ),
            "last_synchronized_at": (
                sync_status.last_synchronized_at.isoformat()
                if sync_status.last_synchronized_at is not None
                else None
            ),
            "latest_sync_record": (
                sync_status.latest_sync_record.model_dump(mode="json")
                if sync_status.latest_sync_record is not None
                else None
            ),
        }

        generated_at = datetime.now(UTC)
        package_version = self._compute_package_version(
            memory_version=memory_response.memory_version,
            snapshot_version=(
                int(transcript["snapshot_version"]) if transcript is not None else 0
            ),
            sync_version=sync_status.sync_version,
            context_package_version=(
                int(latest_context_package["version"])
                if latest_context_package is not None
                else 0
            ),
        )

        payload: dict[str, Any] = {
            "repository_branch_id": str(repository_branch_id),
            "package_version": package_version,
            "generated_at": generated_at.isoformat(),
            "workspace": graph["workspace"],
            "project": graph["project"],
            "repository": graph["repository"],
            "repository_branch": graph["repository_branch"],
            "repository_memory": repository_memory,
            "transcript_snapshot": transcript,
            "latest_context_package": latest_context_package,
            "latest_commit": latest_commit,
            "sync": sync,
            "active_developer": active_developer,
        }
        payload["markdown_content"] = self._render_markdown(payload)
        return payload

    async def get_package(self, branch: RepositoryBranch) -> PullPackageResponse:
        payload = await self.build_pull_package(branch.id)
        return self._to_response(payload)

    async def export_markdown(self, branch: RepositoryBranch) -> PullPackageExportResponse:
        payload = await self.build_pull_package(branch.id)
        return PullPackageExportResponse(
            filename=f"pull-package-{branch.name}.md",
            content=payload["markdown_content"],
            content_type="text/markdown",
        )

    async def export_json(self, branch: RepositoryBranch) -> PullPackageJsonExportResponse:
        payload = await self.build_pull_package(branch.id)
        content = {key: value for key, value in payload.items() if key != "markdown_content"}
        return PullPackageJsonExportResponse(
            filename=f"pull-package-{branch.name}.json",
            content=content,
        )

    def _to_response(self, payload: dict[str, Any]) -> PullPackageResponse:
        return PullPackageResponse(
            repository_branch_id=UUID(payload["repository_branch_id"]),
            package_version=payload["package_version"],
            generated_at=datetime.fromisoformat(payload["generated_at"]),
            workspace=payload["workspace"],
            project=payload["project"],
            repository=payload["repository"],
            repository_branch=payload["repository_branch"],
            repository_memory=payload["repository_memory"],
            transcript_snapshot=payload["transcript_snapshot"],
            latest_context_package=payload["latest_context_package"],
            latest_commit=payload["latest_commit"],
            sync=payload["sync"],
            active_developer=payload["active_developer"],
            markdown_content=payload["markdown_content"],
            json_content={
                key: value for key, value in payload.items() if key != "markdown_content"
            },
        )

    def _compute_package_version(
        self,
        *,
        memory_version: int,
        snapshot_version: int,
        sync_version: int,
        context_package_version: int,
    ) -> int:
        total = memory_version + snapshot_version + sync_version + context_package_version
        return total if total > 0 else 1

    async def _load_branch_and_repository(
        self,
        repository_branch_id: UUID,
    ) -> tuple[RepositoryBranch, Repository]:
        result = await self.db.execute(
            select(RepositoryBranch, Repository)
            .options(noload("*"))
            .join(Repository, Repository.id == RepositoryBranch.repository_id)
            .where(RepositoryBranch.id == repository_branch_id)
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository branch not found",
            )
        return row[0], row[1]

    async def _load_metadata(
        self,
        branch: RepositoryBranch,
        repository: Repository,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                Workspace.id.label("workspace_id"),
                Workspace.name.label("workspace_name"),
                Workspace.slug.label("workspace_slug"),
            )
            .select_from(Repository)
            .join(Project, Project.id == Repository.project_id)
            .join(Workspace, Workspace.id == Repository.workspace_id)
            .where(Repository.id == repository.id)
        )
        row = result.one()
        return {
            "workspace": {
                "id": str(row.workspace_id),
                "name": row.workspace_name,
                "slug": row.workspace_slug,
            },
            "project": {
                "id": str(row.project_id),
                "name": row.project_name,
            },
            "repository": {
                "id": str(repository.id),
                "name": repository.name,
                "provider": (
                    repository.provider.value
                    if hasattr(repository.provider, "value")
                    else repository.provider
                ),
                "owner": repository.owner,
                "repository_name": repository.repository_name,
                "remote_url": repository.remote_url,
                "default_branch": repository.default_branch,
            },
            "repository_branch": {
                "id": str(branch.id),
                "name": branch.name,
                "is_default": branch.is_default,
                "is_active": branch.is_active,
            },
        }

    async def _load_latest_transcript_snapshot(
        self,
        repository_branch_id: UUID,
    ) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(
                TranscriptSnapshot.id,
                TranscriptSnapshot.external_ai_session_id,
                TranscriptSnapshot.snapshot_version,
                TranscriptSnapshot.content,
                TranscriptSnapshot.character_count,
                TranscriptSnapshot.created_at,
                TranscriptSnapshot.updated_at,
            )
            .join(
                ExternalAISession,
                ExternalAISession.id == TranscriptSnapshot.external_ai_session_id,
            )
            .where(ExternalAISession.repository_branch_id == repository_branch_id)
            .order_by(
                TranscriptSnapshot.updated_at.desc(),
                TranscriptSnapshot.id.desc(),
            )
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return {
            "id": str(row.id),
            "external_ai_session_id": str(row.external_ai_session_id),
            "snapshot_version": row.snapshot_version,
            "character_count": row.character_count,
            "content": row.content,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

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

    def _render_markdown(self, payload: dict[str, Any]) -> str:
        workspace = payload["workspace"]
        project = payload["project"]
        repository = payload["repository"]
        branch = payload["repository_branch"]
        memory = payload["repository_memory"]
        transcript = payload["transcript_snapshot"]
        latest_package = payload["latest_context_package"]
        latest_commit = payload["latest_commit"]
        sync = payload["sync"]
        active_developer = payload["active_developer"]

        lines: list[str] = [
            "# Repository",
            "",
            f"- workspace: {workspace['name']}",
            f"- project: {project['name']}",
            f"- repository: {repository['name']}",
            f"- owner: {repository['owner']}",
            f"- remote: {repository['remote_url']}",
            f"- branch: {branch['name']}",
            "",
            "# Repository Memory",
            "",
        ]
        if memory is None:
            lines.append("- repository memory: Not Available Yet")
        else:
            lines.append(f"- memory version: {memory['memory_version']}")
            lines.append(f"- generated at: {memory['generated_at']}")
            if memory.get("latest_commit_hash"):
                lines.append(f"- latest commit: #{memory['latest_commit_hash']}")
            lines.append("")
            lines.append(memory.get("markdown_content") or "")

        lines.extend(["", "# Transcript Snapshot", ""])
        if transcript is None:
            lines.append("- transcript snapshot: Not Available Yet")
        else:
            lines.append(f"- snapshot version: {transcript['snapshot_version']}")
            lines.append(f"- character count: {transcript['character_count']}")
            lines.append(f"- updated at: {transcript['updated_at']}")
            lines.append("")
            lines.append(transcript.get("content") or "")

        lines.extend(["", "# Latest Context Package", ""])
        if latest_package is None:
            lines.append("- latest context package: Not Available Yet")
        else:
            lines.append(f"- package id: {latest_package['id']}")
            lines.append(f"- version: {latest_package['version']}")
            lines.append(f"- commit: #{latest_package['commit_hash']}")
            lines.append(f"- generated at: {latest_package['generated_at']}")

        lines.extend(["", "# Latest Commit", ""])
        if latest_commit is None:
            lines.append("- latest commit: Not Available Yet")
        else:
            lines.append(f"- commit: #{latest_commit['commit_hash']}")
            lines.append(f"- title: {latest_commit['title']}")
            lines.append(f"- created at: {latest_commit['created_at']}")

        lines.extend(
            [
                "",
                "# Sync Information",
                "",
                f"- sync version: {sync['sync_version']}",
                f"- sync state: {sync['sync_state']}",
                f"- last synchronized at: {sync['last_synchronized_at'] or 'Never'}",
                "",
                "# Active Developer",
                "",
            ]
        )
        if active_developer is None:
            lines.append("- active developer: None")
        else:
            lines.append(f"- developer: {active_developer['user_name']}")
            lines.append(f"- status: {active_developer['status']}")
            lines.append(
                f"- client: {active_developer.get('client_name') or '—'} "
                f"{active_developer.get('client_version') or ''}".rstrip()
            )
            lines.append(f"- last heartbeat: {active_developer['last_heartbeat_at']}")

        lines.append("")
        return "\n".join(lines)
