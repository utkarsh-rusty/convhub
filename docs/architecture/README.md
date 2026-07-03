# Architecture documentation

ConvHub is **Git for AI-native Project Memory**. These documents describe how the system is structured and which parts are implemented versus planned.

## Architecture Index

| Document | Status |
|----------|--------|
| [Architecture overview](architecture-overview.md) | Implemented |
| [Project Memory](project-memory.md) | Primitives implemented; packages **Planned** |
| [Conversation Model](conversation-model.md) | Implemented |
| [Commit Model](commit-model.md) | Implemented |
| [Branch Model](branch-model.md) | Implemented |
| [Ownership Routing](ADR-010-ownership-first-routing.md) | Implemented |
| [Borrowing](ADR-009-resource-sharing.md) | Implemented |
| [Realtime](realtime-events.md) | Implemented |
| [Context Packages](context-packages.md) | Planned |
| [Git Integration](git-integration.md) | Planned |
| [VS Code Extension](vscode-extension.md) | Planned |

## Flow diagrams (implemented)

| Topic | Document |
|-------|----------|
| Authentication | [authentication-flow.md](authentication-flow.md) |
| Workspaces | [workspace-model.md](workspace-model.md) |
| Conversations | [conversation-lifecycle.md](conversation-lifecycle.md), [conversation-model.md](conversation-model.md) |
| Routing | [ADR-008-routing-engine.md](ADR-008-routing-engine.md), [ADR-010-ownership-first-routing.md](ADR-010-ownership-first-routing.md) |
| Borrowing | [ADR-009-resource-sharing.md](ADR-009-resource-sharing.md) |
| Credits | [ADR-006-credit-ledger.md](ADR-006-credit-ledger.md), [ADR-007-credit-policy.md](ADR-007-credit-policy.md) |
| Realtime | [realtime-events.md](realtime-events.md) |
| Providers | [provider-abstraction.md](provider-abstraction.md) |
| AI account ownership | [ai-account-ownership.md](ai-account-ownership.md) |
| Commits | [commit-model.md](commit-model.md), [ADR-011-conversation-commits.md](ADR-011-conversation-commits.md) |
| Branches | [branch-model.md](branch-model.md) |

## Architecture Decision Records (ADRs)

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-005](ADR-005-prompt-builder.md) | Prompt builder | Implemented |
| [ADR-006](ADR-006-credit-ledger.md) | Credit ledger | Implemented |
| [ADR-007](ADR-007-credit-policy.md) | Credit policy | Implemented |
| [ADR-008](ADR-008-routing-engine.md) | Routing engine | Implemented |
| [ADR-009](ADR-009-resource-sharing.md) | Resource sharing | Implemented |
| [ADR-010](ADR-010-ownership-first-routing.md) | Ownership-first routing | Implemented |
| [ADR-011](ADR-011-conversation-commits.md) | Conversation commits and checkpoints | Implemented |

## Principles

See also [../architecture.md](../architecture.md).
