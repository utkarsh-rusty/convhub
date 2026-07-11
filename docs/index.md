# ConvHub Documentation

**Git changed how developers collaborate on code. ConvHub changes how developers collaborate with AI.**

Git versions code. ConvHub versions AI collaboration context and project memory — while every developer keeps ownership of their providers.

## Start here

| Document | Description |
|----------|-------------|
| [README](../README.md) | Product overview, features, plugin guide, FAQ |
| [Architecture overview](architecture/architecture-overview.md) | End-to-end system flow |
| [Coding workspaces](architecture/coding-workspaces.md) | Repos, memory, Claude handoff |
| [Claude plugin](../plugins/claude/README.md) | Hooks + `convhub push` / `pull` |
| [Roadmap](../roadmap.md) | MVP complete through Sprint 36 + future |
| [Known limitations](../KNOWN_LIMITATIONS.md) | Beta caveats |
| [Contributing](../CONTRIBUTING.md) | How to contribute |

## Architecture

| Topic | Document | Status |
|-------|----------|--------|
| Index | [architecture/README.md](architecture/README.md) | — |
| Overview | [architecture-overview.md](architecture/architecture-overview.md) | Implemented |
| Projects | [projects.md](architecture/projects.md) | Implemented |
| Project Memory | [project-memory.md](architecture/project-memory.md) | Primitives + packages implemented |
| Coding Workspaces | [coding-workspaces.md](architecture/coding-workspaces.md) | Implemented |
| Context Packages | [context-packages.md](architecture/context-packages.md) | Implemented |
| Context Restore | [context-restore.md](architecture/context-restore.md) | Implemented |
| Conversation Model | [conversation-model.md](architecture/conversation-model.md) | Implemented |
| Commit Model | [commit-model.md](architecture/commit-model.md) | Implemented |
| Branch Model | [branch-model.md](architecture/branch-model.md) | Implemented |
| Ownership Routing | [ADR-010](architecture/ADR-010-ownership-first-routing.md) | Implemented |
| Borrowing | [ADR-009](architecture/ADR-009-resource-sharing.md) | Implemented |
| Realtime | [realtime-events.md](architecture/realtime-events.md) | Implemented |
| Git Integration | [git-integration.md](architecture/git-integration.md) | Metadata implemented; automation planned |
| VS Code Extension | [vscode-extension.md](architecture/vscode-extension.md) | Planned |

## Architecture Decision Records (ADRs)

| ADR | Topic | Status |
|-----|-------|--------|
| [ADR-005](architecture/ADR-005-prompt-builder.md) | Prompt builder | Implemented |
| [ADR-006](architecture/ADR-006-credit-ledger.md) | Credit ledger | Implemented |
| [ADR-007](architecture/ADR-007-credit-policy.md) | Credit policy | Implemented |
| [ADR-008](architecture/ADR-008-routing-engine.md) | Routing engine | Implemented |
| [ADR-009](architecture/ADR-009-resource-sharing.md) | Resource sharing and borrowing | Implemented |
| [ADR-010](architecture/ADR-010-ownership-first-routing.md) | Ownership-first routing | Implemented |
| [ADR-011](architecture/ADR-011-conversation-commits.md) | Conversation commits and checkpoints | Implemented |
| [ADR-012](architecture/ADR-012-context-packages.md) | Context Packages | Implemented |
| [ADR-013](architecture/ADR-013-context-restore.md) | Context Restore | Implemented |
| [ADR-014](architecture/ADR-014-projects.md) | First-class Projects | Implemented |

## Principles

See [architecture.md](architecture.md) for core design principles.
