"""Static Claude handoff instruction block."""

CLAUDE_HANDOFF_INSTRUCTIONS = (
    "You are continuing work that was previously performed in another Claude Code session. "
    "Treat the above information as the current project state and continue from here."
)


def _fmt(value: object | None, fallback: str = "Not Available Yet") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def render_claude_handoff(pull_package: dict) -> str:
    """Convert a Pull Package dict into Claude handoff Markdown. Formatting only."""
    workspace = pull_package.get("workspace") or {}
    project = pull_package.get("project") or {}
    repository = pull_package.get("repository") or {}
    branch = pull_package.get("repository_branch") or {}
    memory = pull_package.get("repository_memory")
    transcript = pull_package.get("transcript_snapshot")
    latest_package = pull_package.get("latest_context_package")
    latest_commit = pull_package.get("latest_commit")
    sync = pull_package.get("sync") or {}
    active_developer = pull_package.get("active_developer")

    lines: list[str] = [
        "# ConvHub Project Handoff",
        "",
        "## Repository",
        "",
        f"- name: {_fmt(repository.get('name'))}",
        f"- provider: {_fmt(repository.get('provider'))}",
        f"- owner: {_fmt(repository.get('owner'))}",
        f"- repository name: {_fmt(repository.get('repository_name'))}",
        f"- remote url: {_fmt(repository.get('remote_url'))}",
        "",
        "## Workspace",
        "",
        f"- name: {_fmt(workspace.get('name'))}",
        f"- slug: {_fmt(workspace.get('slug'))}",
        "",
        "## Project",
        "",
        f"- name: {_fmt(project.get('name'))}",
        "",
        "## Repository Branch",
        "",
        f"- name: {_fmt(branch.get('name'))}",
        f"- default: {_fmt(branch.get('is_default'))}",
        f"- active: {_fmt(branch.get('is_active'))}",
        "",
        "## Current Repository Memory",
        "",
    ]

    if not memory:
        lines.append("- repository memory: Not Available Yet")
    else:
        lines.append(f"- memory version: {_fmt(memory.get('memory_version'))}")
        lines.append(f"- generated at: {_fmt(memory.get('generated_at'))}")
        if memory.get("latest_commit_hash"):
            lines.append(f"- latest commit: #{memory['latest_commit_hash']}")
        if memory.get("latest_context_package_version") is not None:
            lines.append(
                f"- latest context package: v{memory['latest_context_package_version']}"
            )
        markdown_content = memory.get("markdown_content") or ""
        if markdown_content:
            lines.append("")
            lines.append(markdown_content.rstrip())

    lines.extend(["", "## Latest Context Package", ""])
    if not latest_package:
        lines.append("- latest context package: Not Available Yet")
    else:
        lines.append(f"- id: {_fmt(latest_package.get('id'))}")
        lines.append(f"- version: {_fmt(latest_package.get('version'))}")
        lines.append(f"- commit: #{_fmt(latest_package.get('commit_hash'))}")
        lines.append(f"- generated at: {_fmt(latest_package.get('generated_at'))}")

    lines.extend(["", "## Current Commit", ""])
    if not latest_commit:
        lines.append("- current commit: Not Available Yet")
    else:
        lines.append(f"- commit: #{_fmt(latest_commit.get('commit_hash'))}")
        lines.append(f"- title: {_fmt(latest_commit.get('title'))}")
        lines.append(f"- created at: {_fmt(latest_commit.get('created_at'))}")

    lines.extend(["", "## Transcript Snapshot", ""])
    if not transcript:
        lines.append("- transcript snapshot: Not Available Yet")
    else:
        lines.append(f"- snapshot version: {_fmt(transcript.get('snapshot_version'))}")
        lines.append(f"- character count: {_fmt(transcript.get('character_count'))}")
        lines.append(f"- updated at: {_fmt(transcript.get('updated_at'))}")
        content = transcript.get("content") or ""
        if content:
            lines.append("")
            lines.append(content.rstrip())

    lines.extend(["", "## Active Developer", ""])
    if not active_developer:
        lines.append("- active developer: None")
    else:
        lines.append(f"- developer: {_fmt(active_developer.get('user_name'))}")
        lines.append(f"- status: {_fmt(active_developer.get('status'))}")
        client = " ".join(
            part
            for part in (
                active_developer.get("client_name"),
                active_developer.get("client_version"),
            )
            if part
        )
        lines.append(f"- client: {_fmt(client or None)}")
        lines.append(f"- last heartbeat: {_fmt(active_developer.get('last_heartbeat_at'))}")

    lines.extend(
        [
            "",
            "## Current Sync Status",
            "",
            f"- sync version: {_fmt(sync.get('sync_version'))}",
            f"- sync state: {_fmt(sync.get('sync_state'))}",
            f"- last synchronized at: {_fmt(sync.get('last_synchronized_at'), 'Never')}",
            "",
            "## Instructions",
            "",
            CLAUDE_HANDOFF_INSTRUCTIONS,
            "",
        ]
    )
    return "\n".join(lines)
