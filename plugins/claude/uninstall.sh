#!/usr/bin/env bash
# Remove ConvHub Claude Code hook handlers from ~/.claude/settings.json
set -euo pipefail

CLAUDE_SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
  echo "No Claude settings at $CLAUDE_SETTINGS — nothing to uninstall."
  exit 0
fi

"$PYTHON_BIN" - "$CLAUDE_SETTINGS" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
marker = "convhub-claude-plugin"
settings = json.loads(settings_path.read_text(encoding="utf-8") or "{}")
hooks = settings.get("hooks") or {}

def is_ours(handler: dict) -> bool:
    if handler.get("convhub_plugin") == marker:
        return True
    command = str(handler.get("command") or "")
    return "plugins/claude/hooks/" in command.replace("\\", "/")

changed = False
for event in list(hooks.keys()):
    groups = hooks.get(event) or []
    cleaned_groups = []
    for group in groups:
        handlers = [
            h for h in group.get("hooks", [])
            if not (isinstance(h, dict) and is_ours(h))
        ]
        if handlers:
            cleaned_groups.append({**group, "hooks": handlers})
        else:
            changed = True
        if len(handlers) != len(group.get("hooks", [])):
            changed = True
    if cleaned_groups:
        hooks[event] = cleaned_groups
    else:
        hooks.pop(event, None)
        changed = True

settings["hooks"] = hooks
settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
print(f"Removed ConvHub Claude hooks from {settings_path}" if changed else "No ConvHub hooks found.")
PY

BIN_DIR="${CONVHUB_BIN_DIR:-$HOME/.local/bin}"
if [[ -L "$BIN_DIR/convhub" ]]; then
  TARGET="$(readlink "$BIN_DIR/convhub" || true)"
  if [[ "$TARGET" == *"/plugins/claude/convhub" ]]; then
    rm -f "$BIN_DIR/convhub"
    echo "Removed CLI symlink: $BIN_DIR/convhub"
  fi
fi

echo "Done."
