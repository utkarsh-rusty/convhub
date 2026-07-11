# Coding Workspaces & Claude Handoff

**Status: Implemented** (MVP through Sprint 36)

## Intent

AI-assisted work sits next to a code repository. ConvHub links **repository metadata** (not remote Git automation) to collaborative memory so a teammate can continue an AI coding session after `git pull` + `convhub pull`.

## Implemented capabilities

| Capability | Role |
|------------|------|
| Coding repositories / branches | Workspace-scoped repo and branch records |
| Sync metadata | Last sync, active developers, conversation linkage |
| Repository Memory | Deterministic project-state composition for a branch |
| External AI Sessions | Connect / upload transcript chunks / disconnect |
| Transcript Snapshots | Rebuild on upload; export |
| Pull Package | Compose artifacts; JSON / Markdown export |
| Claude Handoff | Markdown adapter for a fresh Claude Code session |
| Claude Code plugin | Official hooks + `convhub push` / `convhub pull` |

## What is not implemented

- ConvHub does **not** run `git` for you or talk to Git remotes.
- Transcripts are **not** LLM-summarized for handoff.
- Other IDE adapters (Cursor, Codex, Gemini tooling, VS Code) are **planned**.

## Plugin entrypoint

See [plugins/claude/README.md](../../plugins/claude/README.md) and the root [README.md](../../README.md) Plugin Guide.

## Related

- [git-integration.md](git-integration.md) — remote Git automation (planned)
- [project-memory.md](project-memory.md) — conversation memory primitives
- [roadmap.md](../../roadmap.md)
