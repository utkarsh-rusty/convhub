"""ConvHub CLI entrypoint implementation."""

from __future__ import annotations

import sys

from commands import run_pull, run_push


USAGE = """Usage:
  convhub push
  convhub pull

Push flushes transcript deltas and verifies ConvHub artifacts.
Pull downloads the Claude Handoff Markdown for a fresh session.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        sys.stdout.write(USAGE)
        return 0 if args and args[0] in {"-h", "--help", "help"} else 1

    command = args[0]
    if command == "push":
        result = run_push()
        sys.stdout.write(result.render())
        return result.exit_code
    if command == "pull":
        result = run_pull()
        sys.stdout.write(result.render())
        return result.exit_code

    sys.stderr.write(f"Unknown command: {command}\n\n{USAGE}")
    return 1
