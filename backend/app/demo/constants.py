from __future__ import annotations

from typing import Literal

DemoPersona = Literal["alice", "bob", "charlie"]

DEMO_PASSWORD = "demo12345"
DEMO_WORKSPACE_SLUG = "demo"

DEMO_PERSONAS: dict[DemoPersona, dict[str, str]] = {
    "alice": {
        "name": "Alice",
        "email": "alice@demo.convhub.local",
        "role": "owner",
    },
    "bob": {
        "name": "Bob",
        "email": "bob@demo.convhub.local",
        "role": "member",
    },
    "charlie": {
        "name": "Charlie",
        "email": "charlie@demo.convhub.local",
        "role": "member",
    },
}
