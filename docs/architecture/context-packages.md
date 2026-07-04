# Context Packages

## Status

**Implemented** (Sprint 19) — generation, storage, export.

Future consumers are **Planned** / **Research** and are not built yet.

## Overview

A Context Package is an immutable, portable project-memory artifact bound to exactly one conversation commit.

```
Conversation Commit
        ↓
Context Package (generated, immutable)
        ↓
Export JSON
```

Every successful commit creates one package in the same database transaction. If package generation fails, the commit is rolled back.

## Implemented

- `context_packages` table and SQLAlchemy model
- Deterministic generation (no AI) from existing conversation, commit, participant, provider, credit, and borrow data
- Empty placeholders for `architecture_notes`, `decisions`, and `todos`
- Keyword list derived from metadata only
- APIs:
  - `GET /context-packages/{id}`
  - `GET /commits/{id}/context-package`
  - `GET /conversations/{id}/context-packages`
  - `GET /context-packages/{id}/export`
- UI: View Context Package from commit details, export JSON

## Planned consumers (not implemented)

| Consumer | Status |
|----------|--------|
| Context Restore | **Implemented** |
| Git Integration | Planned |
| VS Code Extension | Planned |
| Claude Code / Cursor / Codex adapters | Planned |
| Conversation Merge | Research |
| Knowledge Graph | Research |

## Not implemented

- Import endpoint
- AI-generated summaries
- Editing packages after creation
