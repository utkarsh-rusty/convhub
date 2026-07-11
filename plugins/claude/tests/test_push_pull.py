"""Tests for Sprint 36 — convhub push / pull workflow."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from cli import main as cli_main  # noqa: E402
from commands import (  # noqa: E402
    PULL_INSTRUCTION,
    default_download_dir,
    run_pull,
    run_push,
)
from config import PluginConfig  # noqa: E402
from state import PluginState, load_state, save_state  # noqa: E402


@pytest.fixture
def convhub_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "convhub-home"
    home.mkdir()
    monkeypatch.setenv("CONVHUB_HOME", str(home))
    return home


@pytest.fixture
def config() -> PluginConfig:
    return PluginConfig(
        server_url="http://localhost:8000/api/v1",
        api_token="token",
        workspace_id="11111111-1111-1111-1111-111111111111",
        repository_id="22222222-2222-2222-2222-222222222222",
        repository_branch_id="33333333-3333-3333-3333-333333333333",
        conversation_id=None,
        machine_identifier="test-machine",
    )


def _mock_client_for_push(*, remote_offset: int = 5) -> MagicMock:
    client = MagicMock()
    client.connect.return_value = {
        "id": "44444444-4444-4444-4444-444444444444",
        "repository_branch_id": "33333333-3333-3333-3333-333333333333",
        "conversation_id": None,
        "last_synced_offset": 0,
        "chunk_count": 0,
    }
    client.upload_chunk.return_value = {"sequence_number": 1}
    client.get_session.return_value = {
        "id": "44444444-4444-4444-4444-444444444444",
        "last_synced_offset": remote_offset,
        "chunk_count": 1,
        "status": "active",
    }
    client.get_snapshot.return_value = {"snapshot_version": 2, "character_count": remote_offset}
    client.get_repository_memory.return_value = {"memory_version": 3}
    client.get_pull_package.return_value = {"package_version": 4}
    client.get_claude_handoff.return_value = "# ConvHub Project Handoff\n"
    return client


def test_push_command_uploads_and_verifies(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("hello", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="44444444-4444-4444-4444-444444444444",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
    )
    client = _mock_client_for_push(remote_offset=5)

    result = run_push(config=config, state=state, client=client)
    assert result.ok is True
    assert result.exit_code == 0
    assert result.uploaded_bytes == 5
    assert "✓ Session synchronized" in result.render()
    assert "✓ Transcript uploaded" in result.render()
    assert "✓ Repository Memory updated" in result.render()
    assert "✓ Pull Package refreshed" in result.render()
    assert "✓ Claude Handoff refreshed" in result.render()
    assert "Done." in result.render()
    client.upload_chunk.assert_called_once()
    client.get_session.assert_called_once()
    client.get_repository_memory.assert_called_once()
    client.get_pull_package.assert_called_once()
    client.get_claude_handoff.assert_called_once()

    saved = load_state()
    assert saved.last_uploaded_offset == 5


def test_repeated_push_is_idempotent(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("hello", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="sess",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
    )
    client = _mock_client_for_push(remote_offset=5)

    first = run_push(config=config, state=state, client=client)
    assert first.ok is True
    assert client.upload_chunk.call_count == 1

    client.get_session.return_value = {
        "id": "sess",
        "last_synced_offset": 5,
        "chunk_count": 1,
        "status": "active",
    }
    second = run_push(config=config, state=load_state(), client=client)
    assert second.ok is True
    # No new bytes — upload not called again
    assert client.upload_chunk.call_count == 1
    assert load_state().last_uploaded_offset == 5


def test_pull_command_saves_handoff(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_dir = tmp_path / "Downloads"
    download_dir.mkdir()
    monkeypatch.setenv("CONVHUB_DOWNLOAD_DIR", str(download_dir))
    monkeypatch.setattr("commands.default_download_dir", lambda: download_dir)

    client = MagicMock()
    client.get_claude_handoff.return_value = "# ConvHub Project Handoff\n\n## Repository\n"

    result = run_pull(config=config, client=client, download_dir=download_dir)
    assert result.ok is True
    assert result.saved_path == download_dir / "convhub-handoff.md"
    assert result.saved_path is not None
    assert result.saved_path.read_text(encoding="utf-8").startswith("# ConvHub Project Handoff")
    rendered = result.render()
    assert "✓ Claude Handoff downloaded" in rendered
    assert "convhub-handoff.md" in rendered
    assert PULL_INSTRUCTION in rendered
    assert "Done." in rendered
    client.get_claude_handoff.assert_called_once_with(config.repository_branch_id)


def test_repeated_pull_overwrites_file(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    download_dir = tmp_path / "out"
    client = MagicMock()
    client.get_claude_handoff.return_value = "version-1"
    first = run_pull(config=config, client=client, download_dir=download_dir)
    assert first.saved_path is not None
    assert first.saved_path.read_text(encoding="utf-8") == "version-1"

    client.get_claude_handoff.return_value = "version-2"
    second = run_pull(config=config, client=client, download_dir=download_dir)
    assert second.ok is True
    assert second.saved_path is not None
    assert second.saved_path.read_text(encoding="utf-8") == "version-2"
    assert client.get_claude_handoff.call_count == 2


def test_push_permission_failure(
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    from convhub_client import ConvHubClientError

    transcript = convhub_home / "t.txt"
    transcript.write_text("x", encoding="utf-8")
    state = PluginState(
        external_ai_session_id="sess",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        dirty=True,
    )
    client = _mock_client_for_push(remote_offset=1)
    client.get_session.side_effect = ConvHubClientError("not found", status=404)
    result = run_push(config=config, state=state, client=client)
    assert result.ok is False
    assert result.exit_code == 1
    assert "Push failed" in result.render()


def test_pull_permission_failure(config: PluginConfig, convhub_home: Path, tmp_path: Path) -> None:
    from convhub_client import ConvHubClientError

    client = MagicMock()
    client.get_claude_handoff.side_effect = ConvHubClientError("denied", status=404)
    result = run_pull(config=config, client=client, download_dir=tmp_path)
    assert result.ok is False
    assert result.exit_code == 1
    assert "Pull failed" in result.render()


def test_cli_main_push_pull(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("abc", encoding="utf-8")
    save_state(
        PluginState(
            external_ai_session_id="sess",
            transcript_path=str(transcript),
            last_uploaded_offset=0,
            next_sequence_number=1,
            dirty=True,
        )
    )

    client = _mock_client_for_push(remote_offset=3)

    def fake_run_push(**kwargs):
        return run_push(config=config, state=load_state(), client=client)

    def fake_run_pull(**kwargs):
        return run_pull(config=config, client=client, download_dir=tmp_path / "dl")

    monkeypatch.setattr("cli.run_push", fake_run_push)
    monkeypatch.setattr("cli.run_pull", fake_run_pull)

    assert cli_main(["push"]) == 0
    out = capsys.readouterr().out
    assert "✓ Session synchronized" in out

    client.get_claude_handoff.return_value = "# handoff\n"
    assert cli_main(["pull"]) == 0
    out = capsys.readouterr().out
    assert "✓ Claude Handoff downloaded" in out
    assert (tmp_path / "dl" / "convhub-handoff.md").exists()


def test_default_download_dir_env_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom = tmp_path / "custom-downloads"
    monkeypatch.setenv("CONVHUB_DOWNLOAD_DIR", str(custom))
    assert default_download_dir() == custom


def test_end_to_end_plugin_orchestration(
    tmp_path: Path,
    config: PluginConfig,
    convhub_home: Path,
) -> None:
    """Push then pull against mocked APIs — full plugin orchestration path."""
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b"line-one\n")
    state = PluginState(
        external_ai_session_id="sess-e2e",
        transcript_path=str(transcript),
        last_uploaded_offset=0,
        next_sequence_number=1,
        dirty=True,
    )
    client = _mock_client_for_push(remote_offset=9)
    client.get_claude_handoff.return_value = "# ConvHub Project Handoff\n\npaste me\n"

    push = run_push(config=config, state=state, client=client)
    assert push.ok is True
    assert load_state().last_uploaded_offset == 9

    # Append more work and push again
    with transcript.open("ab") as handle:
        handle.write(b"line-two\n")
    client.get_session.return_value = {
        "id": "sess-e2e",
        "last_synced_offset": 18,
        "chunk_count": 2,
        "status": "active",
    }
    push2 = run_push(config=config, state=load_state(), client=client)
    assert push2.ok is True
    assert client.upload_chunk.call_count == 2
    assert load_state().last_uploaded_offset == 18

    download_dir = tmp_path / "Downloads"
    pull = run_pull(config=config, client=client, download_dir=download_dir)
    assert pull.ok is True
    assert pull.saved_path is not None
    assert "paste me" in pull.saved_path.read_text(encoding="utf-8")
