"""Shared ConvHub Claude hook orchestration."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

from config import PluginConfig, load_config
from convhub_client import ConvHubClient, ConvHubClientError
from state import PluginState, load_state, save_state


SUPPORTED_EVENTS = frozenset(
    {"SessionStart", "PostToolUse", "Stop", "PreCompact", "SessionEnd"}
)


def read_hook_payload(stdin=None) -> dict[str, Any]:
    stream = stdin if stdin is not None else sys.stdin
    raw = stream.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def machine_identifier(config: PluginConfig) -> str:
    if config.machine_identifier:
        return config.machine_identifier
    host = socket.gethostname()
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
    return f"{user}@{host}"


def handle_session_start(
    payload: dict[str, Any],
    *,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> PluginState:
    config = config or load_config()
    state = state or load_state()
    client = client or ConvHubClient(config)

    session = client.connect(
        provider="claude_code",
        machine_identifier=machine_identifier(config),
        conversation_id=config.conversation_id,
    )
    state.external_ai_session_id = str(session["id"])
    state.repository_branch_id = str(
        session.get("repository_branch_id") or config.repository_branch_id
    )
    state.conversation_id = (
        str(session["conversation_id"])
        if session.get("conversation_id")
        else config.conversation_id
    )
    state.last_uploaded_offset = int(session.get("last_synced_offset") or 0)
    state.next_sequence_number = int(session.get("chunk_count") or 0) + 1
    state.dirty = False
    transcript_path = payload.get("transcript_path")
    if transcript_path:
        state.transcript_path = str(transcript_path)
    save_state(state)
    return state


def handle_post_tool_use(
    payload: dict[str, Any],
    *,
    state: PluginState | None = None,
) -> PluginState:
    state = state or load_state()
    transcript_path = payload.get("transcript_path")
    # Mark dirty only — never upload from PostToolUse.
    state.mark_dirty(str(transcript_path) if transcript_path else None)
    save_state(state)
    return state


def read_transcript_delta(
    transcript_path: str,
    last_uploaded_offset: int,
) -> tuple[str, int, int]:
    """Return (raw_content, start_offset, end_offset) using byte offsets."""
    path = Path(transcript_path)
    if not path.exists():
        return "", last_uploaded_offset, last_uploaded_offset
    size = path.stat().st_size
    start = max(0, min(last_uploaded_offset, size))
    with path.open("rb") as handle:
        handle.seek(start)
        data = handle.read()
    if not data:
        return "", start, start
    content = data.decode("utf-8", errors="replace")
    end = start + len(data)
    return content, start, end


def flush_transcript(
    *,
    force: bool = False,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> PluginState:
    """Upload pending transcript bytes if dirty (or force). Idempotent when clean."""
    config = config or load_config()
    state = state or load_state()
    client = client or ConvHubClient(config)

    if not force and not state.dirty:
        return state
    if not state.external_ai_session_id:
        return state
    if not state.transcript_path:
        state.dirty = False
        save_state(state)
        return state

    content, start, end = read_transcript_delta(
        state.transcript_path,
        state.last_uploaded_offset,
    )
    if not content or end <= start:
        state.dirty = False
        save_state(state)
        return state

    # Skip duplicate upload when offset already caught up.
    if start != state.last_uploaded_offset:
        state.last_uploaded_offset = start

    client.upload_chunk(
        session_id=state.external_ai_session_id,
        sequence_number=state.next_sequence_number,
        start_offset=start,
        end_offset=end,
        raw_content=content,
    )
    state.mark_flushed(end, sequence_increment=True)
    save_state(state)
    return state


def handle_stop(
    payload: dict[str, Any],
    *,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> PluginState:
    state = state or load_state()
    if payload.get("transcript_path"):
        state.transcript_path = str(payload["transcript_path"])
        save_state(state)
    if state.dirty:
        return flush_transcript(config=config, state=state, client=client)
    return state


def handle_pre_compact(
    payload: dict[str, Any],
    *,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> PluginState:
    state = state or load_state()
    if payload.get("transcript_path"):
        state.transcript_path = str(payload["transcript_path"])
        # Always attempt flush before compaction.
        state.dirty = True
        save_state(state)
    return flush_transcript(force=True, config=config, state=state, client=client)


def handle_session_end(
    payload: dict[str, Any],
    *,
    config: PluginConfig | None = None,
    state: PluginState | None = None,
    client: ConvHubClient | None = None,
) -> PluginState:
    config = config or load_config()
    state = state or load_state()
    client = client or ConvHubClient(config)

    if payload.get("transcript_path"):
        state.transcript_path = str(payload["transcript_path"])
        state.dirty = True
        save_state(state)

    state = flush_transcript(force=True, config=config, state=state, client=client)

    if state.external_ai_session_id:
        try:
            client.disconnect(state.external_ai_session_id)
        except ConvHubClientError:
            # Best-effort disconnect; still clear local session binding.
            pass
        state.external_ai_session_id = None
        state.dirty = False
        save_state(state)
    return state


def dispatch(event_name: str, payload: dict[str, Any]) -> None:
    if event_name not in SUPPORTED_EVENTS:
        return
    if event_name == "SessionStart":
        handle_session_start(payload)
    elif event_name == "PostToolUse":
        handle_post_tool_use(payload)
    elif event_name == "Stop":
        handle_stop(payload)
    elif event_name == "PreCompact":
        handle_pre_compact(payload)
    elif event_name == "SessionEnd":
        handle_session_end(payload)


def run_hook(event_name: str) -> int:
    try:
        payload = read_hook_payload()
        # Prefer explicit hook_event_name from Claude when present.
        event = payload.get("hook_event_name") or event_name
        if event not in SUPPORTED_EVENTS:
            return 0
        dispatch(str(event), payload)
        return 0
    except Exception as exc:  # noqa: BLE001 — hooks must not crash Claude
        sys.stderr.write(f"convhub claude plugin error ({event_name}): {exc}\n")
        return 0
