"""Tests for install/uninstall Claude settings merge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def test_install_and_uninstall_hooks(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {"type": "command", "command": "echo keep-me"},
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "CLAUDE_SETTINGS_PATH": str(settings_path),
        "CONVHUB_HOME": str(tmp_path / "convhub"),
        "PYTHON_BIN": sys.executable,
    }
    install = subprocess.run(
        ["bash", str(PLUGIN_ROOT / "install.sh")],
        cwd=PLUGIN_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Installed ConvHub Claude hooks" in install.stdout

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    for event in ("SessionStart", "PostToolUse", "Stop", "PreCompact", "SessionEnd"):
        assert event in settings["hooks"]
        commands = [
            handler["command"]
            for group in settings["hooks"][event]
            for handler in group["hooks"]
        ]
        assert any("plugins/claude/hooks/" in cmd or "hooks/" in cmd for cmd in commands)

    # Existing Stop hook preserved
    stop_commands = [
        handler["command"]
        for group in settings["hooks"]["Stop"]
        for handler in group["hooks"]
    ]
    assert any(cmd == "echo keep-me" for cmd in stop_commands)

    uninstall = subprocess.run(
        ["bash", str(PLUGIN_ROOT / "uninstall.sh")],
        cwd=PLUGIN_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Removed ConvHub Claude hooks" in uninstall.stdout or "No ConvHub hooks" in uninstall.stdout

    settings_after = json.loads(settings_path.read_text(encoding="utf-8"))
    stop_commands_after = [
        handler["command"]
        for group in settings_after.get("hooks", {}).get("Stop", [])
        for handler in group.get("hooks", [])
    ]
    assert "echo keep-me" in stop_commands_after
    for event in ("SessionStart", "PostToolUse", "PreCompact", "SessionEnd"):
        remaining = settings_after.get("hooks", {}).get(event, [])
        for group in remaining:
            for handler in group.get("hooks", []):
                assert handler.get("convhub_plugin") != "convhub-claude-plugin"
