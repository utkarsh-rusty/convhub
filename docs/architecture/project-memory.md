# Project Memory

## Status

| Layer | Status |
|-------|--------|
| Conversations, commits, branches as memory primitives | **Implemented** |
| Context Packages (portable commit memory) | **Implemented** |
| Context Restore (project checkpoints) | **Implemented** |
| Decision Tracking UX | **Planned** (v1.1) |
| Git-linked project memory | **Planned** (v1.2) |
| Semantic restore and knowledge graph | **Research** (v2.0) |

## Vision

Git versions code. ConvHub versions **project memory** — the durable understanding of how a system was designed, debated, and built with AI.

Project memory includes:

- Conversations
- Commits (manual milestones)
- Branches (parallel lines of thought)
- Architecture decisions (captured in chat and commits)
- Provider ownership and execution history
- Collaboration history

## Implemented

Today’s product provides project-knowledge primitives and portable packages:

- Workspace-scoped conversations
- Message history
- Manual conversation commits and automatic checkpoints
- **Context Packages** — immutable, exportable artifacts generated per commit
- **Context Restore** — checkout-style restore into a new working conversation
- Branch lineage and visualization
- Ownership-first routing and borrowing metadata

## Planned

| Item | Status |
|------|--------|
| Decision Tracking | **Planned** |
| Git linkage | **Planned** |
| Semantic restore | **Research** |

These are **not implemented**. See [roadmap.md](../../roadmap.md).

