#!/usr/bin/env python3
"""Claude Code PostToolUse hook — mark transcript dirty (no upload)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime import run_hook  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_hook("PostToolUse"))
