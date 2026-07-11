#!/usr/bin/env bash
# Install ConvHub Claude Code hook handlers into ~/.claude/settings.json
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
mkdir -p "${CONVHUB_HOME:-$HOME/.convhub}"

if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
  echo '{}' > "$CLAUDE_SETTINGS"
fi

"$PYTHON_BIN" - "$PLUGIN_ROOT" "$CLAUDE_SETTINGS" <<'PY'
import json
import sys
from pathlib import Path

plugin_root = Path(sys.argv[1]).resolve()
settings_path = Path(sys.argv[2])
marker = "convhub-claude-plugin"

hooks_map = {
    "SessionStart": plugin_root / "hooks" / "session_start.py",
    "PostToolUse": plugin_root / "hooks" / "post_tool_use.py",
    "Stop": plugin_root / "hooks" / "stop.py",
    "PreCompact": plugin_root / "hooks" / "pre_compact.py",
    "SessionEnd": plugin_root / "hooks" / "session_end.py",
}

settings = json.loads(settings_path.read_text(encoding="utf-8") or "{}")
hooks = settings.setdefault("hooks", {})

def is_ours(handler: dict) -> bool:
    if handler.get("convhub_plugin") == marker:
        return True
    command = str(handler.get("command") or "")
    return "plugins/claude/hooks/" in command.replace("\\", "/")

for event, script in hooks_map.items():
    groups = hooks.get(event, [])
    cleaned = []
    for group in groups:
        handlers = [
            h for h in group.get("hooks", [])
            if not (isinstance(h, dict) and is_ours(h))
        ]
        if handlers:
            cleaned.append({**group, "hooks": handlers})
    command = f'"{sys.executable}" "{script}"'
    entry = {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 30,
                "convhub_plugin": marker,
            }
        ],
    }
    if event == "PostToolUse":
        entry["matcher"] = "*"
    cleaned.append(entry)
    hooks[event] = cleaned

settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
print(f"Installed ConvHub Claude hooks into {settings_path}")
print(f"Plugin root: {plugin_root}")
print("Configure ~/.convhub/config.json before starting Claude Code.")
PY

chmod +x \
  "$PLUGIN_ROOT/hooks/session_start.py" \
  "$PLUGIN_ROOT/hooks/post_tool_use.py" \
  "$PLUGIN_ROOT/hooks/stop.py" \
  "$PLUGIN_ROOT/hooks/pre_compact.py" \
  "$PLUGIN_ROOT/hooks/session_end.py"

CONFIG_PATH="${CONVHUB_HOME:-$HOME/.convhub}/config.json"
if [[ ! -f "$CONFIG_PATH" ]]; then
  cat > "$CONFIG_PATH" <<'EOF'
{
  "server_url": "http://localhost:8000/api/v1",
  "api_token": "REPLACE_WITH_ACCESS_TOKEN",
  "workspace_id": "REPLACE_WITH_WORKSPACE_UUID",
  "repository_id": "REPLACE_WITH_REPOSITORY_UUID",
  "repository_branch_id": "REPLACE_WITH_REPOSITORY_BRANCH_UUID",
  "conversation_id": null
}
EOF
  echo "Wrote starter config at $CONFIG_PATH"
fi

echo "Done."
