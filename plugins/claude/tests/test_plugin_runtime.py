"""Plugin-level tests for ConvHub Claude Hook Integration MVP."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from config import PluginConfig  # noqa: E402
from runtime import (  # noqa: E402
    flush_transcript,
    handle_post_tool_use,
    handle_pre_compact,
    handle_session_end,
    handle_session_start,
    handle_stop,
    read_transcript_delta,
)
from state import PluginState, load_state, save_state  # noqa: E402


@pytest.fixture
def convhub_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "convhub-home"
    home.mkdir()
    monkeypatch.setenv("CONVHUB_HOME", str(home))
    return home


@pytest.fixture
def config(convhub_home: Path) -> PluginConfig:
    return PluginConfig(
        server_url="http://localhost:8000/api/v1",
        api_token="token",
        workspace_id="11111111-1111-1111-1111-111111111111",
        repository_id="22222222-2222-2222-2222-222222222222",
        repository_branch_id="33333333-3333-3333-3333-333333333333",
        conversation_id=None,
        machine_identifier="test-machine",
    )


def test_session_start_creates_session(config: PluginConfig, convhub_home: Path) -> None:
    client = MagicMock()
    client.connect.return_value = {
        "id": "44444444-4444-4444-4444-444444444444",
        "repository_branch_id": config.repository_branch_id,
        "conversation_id": None,
        "last_synced_offset": 0,
        "chunk_count": 0,
    }
    state = handle_session_start(
        {"transcript_path": "/tmp/transcript.jsonl"},
        config=config,
        state=PluginState(),
        client=client,
    )
    client.connect.assert_called_once()
    assert state.external_ai_session_id == "44444444-4444-4444-4444-444444444444"
    assert state.last_uploaded_offset == 0
    assert state.next_sequence_number == 1
    assert state.dirty is False
    saved = load_state()
    assert saved.external_ai_session_id == state.external_ai_session_id


def test_post_tool_use_marks_dirty_without_upload(
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    state = PluginState(external_ai_session_id="sess")
    client = MagicMock()
    updated = handle_post_tool_use(
        {"transcript_path": "/tmp/t.jsonl", "hook_event_name": "PostToolUse"},
        state=state,
    )
    assert updated.dirty is True
    assert updated.transcript_path == "/tmp/t.jsonl"
    client.upload_chunk.assert_not_called()


def test_offset_tracking_and_buffering(tmp_path: Path, config: PluginConfig, convhub_home: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_bytes(b"hello")

    state = PluginState(
        external_ai_session_id="sess",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
    )
    client = MagicMock()
    client.upload_chunk.return_value = {"sequence_number": 1}

    flushed = flush_transcript(config=config, state=state, client=client)
    assert flushed.last_uploaded_offset == 5
    assert flushed.next_sequence_number == 2
    assert flushed.dirty is False
    client.upload_chunk.assert_called_once()
    kwargs = client.upload_chunk.call_args.kwargs
    assert kwargs["start_offset"] == 0
    assert kwargs["end_offset"] == 5
    assert kwargs["raw_content"] == "hello"
    assert kwargs["sequence_number"] == 1

    # Append more bytes and flush again
    with transcript.open("ab") as handle:
        handle.write(b" world")
    flushed.dirty = True
    flushed = flush_transcript(config=config, state=flushed, client=client)
    assert flushed.last_uploaded_offset == 11
    assert client.upload_chunk.call_count == 2
    second = client.upload_chunk.call_args.kwargs
    assert second["start_offset"] == 5
    assert second["end_offset"] == 11
    assert second["raw_content"] == " world"
    assert second["sequence_number"] == 2


def test_duplicate_uploads_do_not_occur(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("abc", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="sess",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
    )
    client = MagicMock()
    client.upload_chunk.return_value = {}

    state = handle_stop({}, config=config, state=state, client=client)
    assert client.upload_chunk.call_count == 1

    # Stop again with clean state — no upload
    state = handle_stop({}, config=config, state=state, client=client)
    assert client.upload_chunk.call_count == 1

    # Flush with no new bytes — no upload
    state.dirty = True
    state = flush_transcript(config=config, state=state, client=client)
    assert client.upload_chunk.call_count == 1
    assert state.dirty is False


def test_pre_compact_flushes(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("compact-me", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="sess",
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=False,
    )
    client = MagicMock()
    client.upload_chunk.return_value = {}

    updated = handle_pre_compact(
        {"transcript_path": str(transcript)},
        config=config,
        state=state,
        client=client,
    )
    assert client.upload_chunk.call_count == 1
    assert updated.last_uploaded_offset == len(b"compact-me")
    assert updated.dirty is False


def test_session_end_flushes_and_disconnects(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("bye", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="sess-1",
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
        transcript_path=str(transcript),
    )
    client = MagicMock()
    client.upload_chunk.return_value = {}
    client.disconnect.return_value = {"status": "closed"}

    updated = handle_session_end({}, config=config, state=state, client=client)
    assert client.upload_chunk.call_count == 1
    client.disconnect.assert_called_once_with("sess-1")
    assert updated.external_ai_session_id is None
    assert updated.dirty is False


def test_read_transcript_delta_seek(tmp_path: Path) -> None:
    path = tmp_path / "t.bin"
    path.write_bytes(b"0123456789")
    content, start, end = read_transcript_delta(str(path), 4)
    assert content == "456789"
    assert start == 4
    assert end == 10


def test_save_and_load_state_roundtrip(convhub_home: Path) -> None:
    state = PluginState(
        external_ai_session_id="abc",
        repository_branch_id="branch",
        conversation_id=None,
        last_uploaded_offset=12,
        last_flush_time="2026-07-11T00:00:00+00:00",
        dirty=True,
    )
    save_state(state)
    loaded = load_state()
    assert loaded.external_ai_session_id == "abc"
    assert loaded.last_uploaded_offset == 12
    assert loaded.dirty is True
    raw = json.loads((convhub_home / "state.json").read_text(encoding="utf-8"))
    assert "external_ai_session_id" in raw
    assert "last_uploaded_offset" in raw
