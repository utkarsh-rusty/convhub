"""Local ConvHub Claude plugin state (~/.convhub/state.json)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from config import convhub_dir


STATE_FILENAME = "state.json"


@dataclass
class PluginState:
    external_ai_session_id: str | None = None
    repository_branch_id: str | None = None
    conversation_id: str | None = None
    last_uploaded_offset: int = 0
    last_flush_time: str | None = None
    next_sequence_number: int = 1
    transcript_path: str | None = None
    dirty: bool = False
    provider: str = "claude_code"

    def mark_dirty(self, transcript_path: str | None = None) -> None:
        self.dirty = True
        if transcript_path:
            self.transcript_path = transcript_path

    def mark_flushed(self, end_offset: int, *, sequence_increment: bool = True) -> None:
        self.last_uploaded_offset = end_offset
        self.last_flush_time = datetime.now(UTC).isoformat()
        self.dirty = False
        if sequence_increment:
            self.next_sequence_number += 1


def state_path() -> Path:
    return convhub_dir() / STATE_FILENAME


def load_state(path: Path | None = None) -> PluginState:
    target = path or state_path()
    if not target.exists():
        return PluginState()
    raw = json.loads(target.read_text(encoding="utf-8"))
    return PluginState(
        external_ai_session_id=raw.get("external_ai_session_id"),
        repository_branch_id=raw.get("repository_branch_id"),
        conversation_id=raw.get("conversation_id"),
        last_uploaded_offset=int(raw.get("last_uploaded_offset") or 0),
        last_flush_time=raw.get("last_flush_time"),
        next_sequence_number=int(raw.get("next_sequence_number") or 1),
        transcript_path=raw.get("transcript_path"),
        dirty=bool(raw.get("dirty", False)),
        provider=str(raw.get("provider") or "claude_code"),
    )


def save_state(state: PluginState, path: Path | None = None) -> None:
    target = path or state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
