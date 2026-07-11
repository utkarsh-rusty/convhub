# ConvHub Roadmap

**Git changed how developers collaborate on code.  
ConvHub changes how developers collaborate with AI.**

Every item is categorized. Future work is never described as shipped.

| Status | Meaning |
|--------|---------|
| **Complete** | Shipped in MVP v1 (through Sprint 36) |
| **Planned** | Intended; not built yet |
| **Research** | Exploratory; design may change |

---

## Complete — MVP v1 (through Sprint 36)

**Status: Complete**

### Collaboration core

- Authentication and workspaces
- First-class Projects (Default Project per workspace)
- Shared conversations and participants
- Multi-provider AI accounts
- Ownership-first routing
- Borrowing engine
- Budgets and credit ledger
- Realtime collaboration (WebSockets, streaming, presence)
- Conversation branching
- Conversation commits and checkpoints
- Context Packages (immutable artifacts per commit)
- Context Restore / Project Checkpoints
- Branch manager, commit graph, and overview visualization
- Open-source MIT distribution

### Coding workspaces & AI handoff

- Coding repositories and repository branches (metadata linkage)
- Repository sync metadata and active developers
- Repository Memory (deterministic composition)
- External AI Sessions and transcript chunk upload
- Transcript Snapshots (rebuild on upload; export)
- Pull Package (JSON / Markdown compose + export)
- Claude Handoff adapter (`GET .../handoff/claude`)
- Claude Code plugin (official hooks)
- `convhub push` / `convhub pull` CLI workflow

---

## Planned — next consumers

**Status: Planned**

- Decision Tracking (fills package placeholders)
- Timeline of project knowledge events
- Richer Project Memory UX on top of packages
- Optional AI summaries (LLM digests — not required for handoff today)

---

## Future — IDE & providers

**Status: Planned**

| Area | Direction |
|------|-----------|
| **Codex adapter** | Handoff / session sync for Codex |
| **Gemini adapter** | Handoff / session sync for Gemini tooling |
| **Cursor adapter** | In-editor / Cursor-native handoff |
| **VS Code Extension** | Push / pull context from the IDE |
| **Git automation** | Remote Git operations beyond ConvHub repository metadata |
| **Enterprise** | SSO, stronger multi-tenant ops, rate limits at scale |

---

## Research — v2.0 Semantic memory & merge

**Status: Research**

- Semantic Context Restore
- Conversation Merge
- Knowledge Graph
- Cross-repository Memory
- AI Merge Assistant

---

See also [README.md](README.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
