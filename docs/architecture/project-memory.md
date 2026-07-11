# Project Memory

## Status

| Layer | Status |
|-------|--------|
| Projects as permanent memory containers | **Implemented** |
| Conversations, commits, branches as memory primitives | **Implemented** |
| Context Packages (portable commit memory) | **Implemented** |
| Context Restore (project checkpoints) | **Implemented** |
| Coding workspaces & Repository Memory | **Implemented** |
| Claude Handoff / Pull Package | **Implemented** |
| Decision Tracking UX | **Planned** |
| Remote Git automation | **Planned** |
| Semantic restore and knowledge graph | **Research** |

## Vision

Git versions code. ConvHub versions **project memory** — the durable understanding of how a system was designed, debated, and built with AI — and hands it to the next developer.

Project memory includes:

- Conversations
- Commits (manual milestones)
- Branches (parallel lines of thought)
- Architecture decisions (captured in chat and commits)
- Repository Memory for coding branches
- Provider ownership and execution history
- Collaboration history

## Implemented

Today’s product provides project-knowledge primitives, portable packages, and coding handoff:

- **Projects** — permanent home for conversations and coding repositories
- Workspace-scoped conversations
- Message history
- Manual conversation commits and automatic checkpoints
- **Context Packages** — immutable, exportable artifacts generated per commit
- **Context Restore** — checkout-style restore into a new working conversation
- **Repository Memory**, Pull Package, and Claude Handoff
- Branch lineage and visualization
- Ownership-first routing and borrowing metadata

## Planned

| Item | Status |
|------|--------|
| Decision Tracking | **Planned** |
| Optional AI summaries | **Planned** |
| Remote Git automation | **Planned** |
| Semantic restore | **Research** |

See [coding-workspaces.md](coding-workspaces.md) and [roadmap.md](../../roadmap.md).
