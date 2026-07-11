# ConvHub Claude Code Plugin (MVP)

Standalone Claude Code plugin that observes sessions with **official Claude Hooks** and synchronizes transcript deltas to ConvHub.

It does **not** poll the filesystem or scan `~/.claude/projects`.
It uses the hook event payload, including `transcript_path`.

## Hooks registered

| Hook | Behavior |
|------|----------|
| `SessionStart` | Create/resume External AI Session via ConvHub API |
| `PostToolUse` | Mark transcript dirty only (no upload) |
| `Stop` | Flush dirty transcript delta |
| `PreCompact` | Always flush before compaction |
| `SessionEnd` | Flush remaining delta + disconnect session |

## Requirements

- Python 3.12+
- Claude Code with hooks support
- ConvHub backend running
- Access token + workspace/repository IDs

## Install

```bash
cd plugins/claude
chmod +x install.sh uninstall.sh
./install.sh
```

This merges ConvHub handlers into `~/.claude/settings.json` and writes a starter `~/.convhub/config.json` if missing.

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

Removes ConvHub hook entries from Claude settings. Does not delete `~/.convhub/`.

## Backend APIs used

- `POST /external-ai-sessions/connect`
- `POST /external-ai-sessions/upload`
- `POST /external-ai-sessions/disconnect`

No new backend endpoints.

## Tests

```bash
cd plugins/claude
python3 -m pytest tests -q
```
