# ADR-012: Context Packages

## Status

Accepted — Sprint 19 · **Implemented** (generation + export)

Context Restore is **Implemented** (Sprint 20). Claude Handoff / Pull Package consumers related coding-memory artifacts are **Implemented**. Package import and additional IDE adapters remain **Planned** / **Research**.

## Context

Conversation commits mark intentional milestones, but tools (restore, handoff, future Git sync / VS Code / merge) need a stable, portable snapshot of project memory at that commit.

## Decision

Introduce **Context Packages** as first-class, immutable artifacts:

- Exactly one package per commit (`commit_id` unique)
- Generated deterministically from existing models (no AI)
- Created in the same transaction as the commit
- Exportable as JSON
- Placeholders for architecture notes, decisions, and todos

## Consequences

### Positive

- Stable contract for restore and future IDE features
- Additive and backwards compatible
- Failure to generate rolls back the commit, keeping history consistent

### Deferred

- Import
- Filling decision/TODO placeholders automatically
