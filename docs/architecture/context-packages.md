# Context Packages

## Status

**Implemented** (Sprint 19) — generation, storage, export.  
**Context Restore** is also **Implemented** (Sprint 20).

Claude Handoff and Pull Package consume related project/coding memory (Sprint 33–34). Additional IDE consumers remain **Planned** / **Research**.

## Overview

A Context Package is an immutable, portable project-memory artifact bound to exactly one conversation commit.

```
Conversation Commit
        ↓
Context Package (generated, immutable)
        ↓
Export JSON  /  Context Restore
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
- Context Restore into a new working conversation

## Consumers

| Consumer | Status |
|----------|--------|
| Context Restore | **Implemented** |
| Pull Package / Claude Handoff | **Implemented** (composes related artifacts) |
| VS Code Extension | Planned |
| Cursor / Codex / Gemini adapters | Planned |
| Remote Git automation | Planned |
| Conversation Merge | Research |
| Knowledge Graph | Research |

## Not implemented

- Import endpoint
- AI-generated summaries
- Editing packages after creation
