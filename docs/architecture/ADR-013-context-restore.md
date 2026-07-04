# ADR-013: Context Restore (Project Checkpoints)

## Status

Accepted — Sprint 20 · **Implemented**

## Context

Context Packages are immutable snapshots. Teams need a way to resume work from a package without mutating history — the Git-checkout pattern.

## Decision

Restore always creates a **new** conversation:

1. Load package and validate workspace access
2. Create a new conversation owned by the restoring user
3. Optionally restore participants, messages, and branch metadata
4. Record restore lineage on the new conversation
5. Leave the original conversation and package unchanged

Do not recreate AIRequest, borrow, credit, or realtime history.

## Consequences

### Positive

- History remains append-only and immutable
- Multiple independent restores from one package are safe
- Restored conversations are normal conversations afterward

### Deferred

- Import of external packages
- In-place checkout (explicitly rejected)
- Automatic decision/TODO population
