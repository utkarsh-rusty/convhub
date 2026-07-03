# Architecture documentation

ConvHub is **GitHub for AI Conversations**. These documents describe how the system is structured and why key decisions were made.

## Overview

| Document | Description |
|----------|-------------|
| [architecture-overview.md](architecture-overview.md) | End-to-end request flow with diagram |

## Flow diagrams

| Topic | Document |
|-------|----------|
| Authentication | [authentication-flow.md](authentication-flow.md) |
| Workspaces | [workspace-model.md](workspace-model.md) |
| Conversations | [conversation-lifecycle.md](conversation-lifecycle.md) |
| Routing | [ADR-008-routing-engine.md](ADR-008-routing-engine.md), [ADR-010-ownership-first-routing.md](ADR-010-ownership-first-routing.md) |
| Borrowing | [ADR-009-resource-sharing.md](ADR-009-resource-sharing.md) |
| Credits | [ADR-006-credit-ledger.md](ADR-006-credit-ledger.md), [ADR-007-credit-policy.md](ADR-007-credit-policy.md) |
| Realtime | [realtime-events.md](realtime-events.md) |
| Providers | [provider-abstraction.md](provider-abstraction.md) |
| AI account ownership | [ai-account-ownership.md](ai-account-ownership.md) |
| Prompt builder | [ADR-005-prompt-builder.md](ADR-005-prompt-builder.md) |

## Architecture Decision Records (ADRs)

| ADR | Title |
|-----|-------|
| [ADR-005](ADR-005-prompt-builder.md) | Prompt builder |
| [ADR-006](ADR-006-credit-ledger.md) | Credit ledger |
| [ADR-007](ADR-007-credit-policy.md) | Credit policy |
| [ADR-008](ADR-008-routing-engine.md) | Routing engine |
| [ADR-009](ADR-009-resource-sharing.md) | Resource sharing |
| [ADR-010](ADR-010-ownership-first-routing.md) | Ownership-first routing |

## Principles

See also [../architecture.md](../architecture.md).
