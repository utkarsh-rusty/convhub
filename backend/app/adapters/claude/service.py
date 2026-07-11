from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.claude.renderer import render_claude_handoff
from app.adapters.claude.schemas import ClaudeHandoffResponse
from app.models.repository_branch import RepositoryBranch
from app.pull_packages.service import PullPackageService


class ClaudeHandoffService:
    """Claude-specific formatter for existing Pull Packages."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.pull_packages = PullPackageService(db)

    async def render_for_branch(self, repository_branch_id: UUID) -> str:
        pull_package = await self.pull_packages.build_pull_package(repository_branch_id)
        return render_claude_handoff(pull_package)

    async def render_for_repository_branch(self, branch: RepositoryBranch) -> str:
        return await self.render_for_branch(branch.id)

    async def export_markdown(self, branch: RepositoryBranch) -> ClaudeHandoffResponse:
        content = await self.render_for_repository_branch(branch)
        return ClaudeHandoffResponse(
            filename=f"claude-handoff-{branch.name}.md",
            content=content,
            content_type="text/markdown",
        )
