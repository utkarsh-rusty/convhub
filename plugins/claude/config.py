"""ConvHub Claude plugin configuration (~/.convhub/config.json)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONVHUB_DIR = Path.home() / ".convhub"
CONFIG_FILENAME = "config.json"


@dataclass
class PluginConfig:
    server_url: str
    api_token: str
    workspace_id: str
    repository_id: str
    repository_branch_id: str
    conversation_id: str | None = None
    machine_identifier: str | None = None

    @property
    def api_base(self) -> str:
        return self.server_url.rstrip("/")


def convhub_dir() -> Path:
    override = os.environ.get("CONVHUB_HOME")
    if override:
        return Path(override).expanduser()
    return DEFAULT_CONVHUB_DIR


def config_path() -> Path:
    return convhub_dir() / CONFIG_FILENAME


def load_config(path: Path | None = None) -> PluginConfig:
    target = path or config_path()
    if not target.exists():
        raise FileNotFoundError(
            f"Missing ConvHub config at {target}. "
            "Create it with server_url, api_token, workspace_id, "
            "repository_id, and repository_branch_id."
        )
    raw = json.loads(target.read_text(encoding="utf-8"))
    required = ("server_url", "api_token", "workspace_id", "repository_id", "repository_branch_id")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"ConvHub config missing required fields: {', '.join(missing)}")
    return PluginConfig(
        server_url=str(raw["server_url"]).rstrip("/"),
        api_token=str(raw["api_token"]),
        workspace_id=str(raw["workspace_id"]),
        repository_id=str(raw["repository_id"]),
        repository_branch_id=str(raw["repository_branch_id"]),
        conversation_id=(str(raw["conversation_id"]) if raw.get("conversation_id") else None),
        machine_identifier=(
            str(raw["machine_identifier"]) if raw.get("machine_identifier") else None
        ),
    )
