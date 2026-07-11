# ConvHub Claude Code Plugin (MVP)

Standalone Claude Code plugin that observes sessions with **official Claude Hooks** and exposes the complete Push/Pull workflow for AI context handoff.

It does **not** poll the filesystem or scan `~/.claude/projects`.  
It uses the hook event payload, including `transcript_path`.

ConvHub does **not** replace Claude Code or Git. After `convhub pull`, you paste the handoff into a **new** Claude Code session yourself.

## Why this exists

Alice finishes a Claude Code session. Bob needs to continue tomorrow.

```text
Alice:  git push && convhub push
Bob:    git pull && convhub pull
Bob:    paste handoff → continue
```

## Hooks registered

| Hook | Behavior |
|------|----------|
| `SessionStart` | Create/resume External AI Session via ConvHub API |
| `PostToolUse` | Mark transcript dirty only (no upload) |
| `Stop` | Flush dirty transcript delta |
| `PreCompact` | Always flush before compaction |
| `SessionEnd` | Flush remaining delta + disconnect session |

## Commands

### `convhub push`

Flush pending transcript, upload deltas, verify session sync, and refresh composed artifacts.

```bash
$ convhub push

✓ Session synchronized
✓ Transcript uploaded
✓ Repository Memory updated
✓ Pull Package refreshed
✓ Claude Handoff refreshed

Done.
```

### `convhub pull`

Download the Claude Handoff Markdown for the configured repository branch.

```bash
$ convhub pull

✓ Claude Handoff downloaded

Saved:

~/Downloads/convhub-handoff.md

Next:

Open a new Claude Code session and paste this document.

Done.
```

Override download directory with `CONVHUB_DOWNLOAD_DIR`.

## Requirements

- Python 3.12+
- Claude Code with hooks support
- ConvHub backend running
- Access token + workspace/repository IDs

## Install

```bash
cd plugins/claude
chmod +x install.sh uninstall.sh convhub
./install.sh
```

This:

1. Registers hooks in `~/.claude/settings.json`
2. Writes starter `~/.convhub/config.json` if missing
3. Symlinks the CLI to `~/.local/bin/convhub`

Override settings path:

```bash
CLAUDE_SETTINGS_PATH=/path/to/settings.json ./install.sh
```

## Configure

Edit `~/.convhub/config.json`:

```json
{
  "server_url": "http://localhost:8000/api/v1",
  "api_token": "<access_token>",
  "workspace_id": "<workspace_uuid>",
  "repository_id": "<repository_uuid>",
  "repository_branch_id": "<repository_branch_uuid>",
  "conversation_id": null
}
```

Replace every `REPLACE_WITH_*` placeholder from the starter file.

Optional: `machine_identifier` (defaults to `user@hostname`).

For tests / alternate home:

```bash
export CONVHUB_HOME=/tmp/convhub-home
```

## Local state

Stored at `~/.convhub/state.json`:

- `external_ai_session_id`
- `repository_branch_id`
- `conversation_id`
- `last_uploaded_offset`
- `last_flush_time`
- plus `next_sequence_number`, `transcript_path`, `dirty`

## Uninstall

```bash
./uninstall.sh
```

Removes ConvHub hook entries and the CLI symlink. Does not delete `~/.convhub/`.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Hooks never sync | Confirm install merged into `~/.claude/settings.json`; restart Claude Code |
| `Push failed` / 401 | Refresh `api_token`; confirm `workspace_id` |
| 404 on repository | Confirm `repository_id` and `repository_branch_id` |
| No transcript upload | Ensure a session started; confirm Stop / `push` after tool use |
| Empty or thin handoff | Create branch memory / commits / external session activity first |
| `convhub: command not found` | Add `~/.local/bin` to `PATH`, or run `./convhub` from this directory |

## Backend APIs used

- `POST /external-ai-sessions/connect`
- `POST /external-ai-sessions/upload`
- `POST /external-ai-sessions/disconnect`
- `GET /external-ai-sessions/{id}`
- `GET /external-ai-sessions/{id}/snapshot`
- `GET /repository-branches/{id}/repository-memory`
- `GET /repository-branches/{id}/pull-package`
- `GET /repository-branches/{id}/handoff/claude`

No new backend endpoints beyond the MVP APIs above.

## Tests

```bash
cd plugins/claude
python3 -m pytest tests -q
```

## Related docs

- [Root README — Plugin Guide](../../README.md#plugin-guide)
- [Coding workspaces architecture](../../docs/architecture/coding-workspaces.md)
- [Known limitations](../../KNOWN_LIMITATIONS.md)
