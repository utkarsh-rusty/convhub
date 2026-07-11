"""Push/Pull workflow commands for the ConvHub Claude plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from config import PluginConfig, load_config
from convhub_client import ConvHubClient, ConvHubClientError
from runtime import flush_transcript, handle_session_start
from state import PluginState, load_state, save_state


HANDOFF_FILENAME = "convhub-handoff.md"
PULL_INSTRUCTION = "Open a new Claude Code session and paste this document."


@dataclass
class CommandResult:
    ok: bool
    lines: list[str] = field(default_factory=list)
    exit_code: int = 0
    saved_path: Path | None = None
    uploaded_bytes: int = 0

    def render(self) -> str:
        return "\n".join(self.lines) + ("\n" if self.lines else "")


def default_download_dir() -> Path:
    override = os.environ.get("CONVHUB_DOWNLOAD_DIR")
    if override:
        return Path(override).expanduser()
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path.home()


def ensure_session(
    *,
    config: PluginConfig,
    state: PluginState,
    client: ConvHubClient,
) -> PluginState:
    """Create/resume an External AI Session when local state has none."""
    if state.external_ai_session_id:
        return state
    return handle_session_start({}, config=config, state=state, client=client)


def run_push(
    *,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> CommandResult:
    config = config or load_config()
    state = state or load_state()
    client = client or ConvHubClient(config)
    lines: list[str] = []

    try:
        offset_before = state.last_uploaded_offset
        state = ensure_session(config=config, state=state, client=client)

        # Force flush so pending transcript bytes upload even if dirty flag is stale.
        state.dirty = True
        state = flush_transcript(force=True, config=config, state=state, client=client)
        uploaded_bytes = max(0, state.last_uploaded_offset - offset_before)

        session = client.get_session(state.external_ai_session_id)  # type: ignore[arg-type]
        remote_offset = int(session.get("last_synced_offset") or 0)
        if remote_offset < state.last_uploaded_offset:
            raise ConvHubClientError(
                "Local offset is ahead of remote last_synced_offset; synchronization failed"
            )
        # Align local offset with server truth after successful push.
        state.last_uploaded_offset = remote_offset
        save_state(state)

        # Touch existing composed artifacts so push verifies the full workflow.
        if state.external_ai_session_id:
            client.get_snapshot(state.external_ai_session_id)
        client.get_repository_memory(config.repository_branch_id)
        client.get_pull_package(config.repository_branch_id)
        client.get_claude_handoff(config.repository_branch_id)

        lines.extend(
            [
                "✓ Session synchronized",
                "✓ Transcript uploaded",
                "✓ Repository Memory updated",
                "✓ Pull Package refreshed",
                "✓ Claude Handoff refreshed",
                "",
                "Done.",
            ]
        )
        return CommandResult(ok=True, lines=lines, uploaded_bytes=uploaded_bytes)
    except (ConvHubClientError, FileNotFoundError, ValueError, OSError) as exc:
        lines = [f"✗ Push failed: {exc}", "", "Done."]
        return CommandResult(ok=False, lines=lines, exit_code=1)


def run_pull(
    *,
    config: PluginConfig | None = None,
    client: ConvHubClient | None = None,
    download_dir: Path | None = None,
    filename: str = HANDOFF_FILENAME,
) -> CommandResult:
    config = config or load_config()
    client = client or ConvHubClient(config)
    target_dir = download_dir or default_download_dir()

    try:
        markdown = client.get_claude_handoff(config.repository_branch_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        target.write_text(markdown, encoding="utf-8")

        display_path = str(target)
        home = str(Path.home())
        if display_path.startswith(home):
            display_path = "~" + display_path[len(home) :]

        lines = [
            "✓ Claude Handoff downloaded",
            "",
            "Saved:",
            "",
            display_path,
            "",
            "Next:",
            "",
            PULL_INSTRUCTION,
            "",
            "Done.",
        ]
        return CommandResult(ok=True, lines=lines, saved_path=target)
    except (ConvHubClientError, FileNotFoundError, ValueError, OSError) as exc:
        lines = [f"✗ Pull failed: {exc}", "", "Done."]
        return CommandResult(ok=False, lines=lines, exit_code=1)
