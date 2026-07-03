# ADR-011: Conversation Commits & Checkpoints

## Status

Accepted — Sprint 17 · **Implemented** (foundation only)

Rollback, cherry-pick, and merge are **not implemented**.

## Context

ConvHub conversations accumulate messages over time. Future Git-inspired features (rollback, merge requests, semantic merge, replay, IDE integration) need an immutable history model that is separate from the live message stream.

Messages alone are insufficient:

- They are mutable in the sense that the conversation continues to grow
- They do not express intentional milestones
- They do not provide a stable parent/child DAG for future merge work

Automatic commits would create noise and force users into a commit-per-message workflow that does not match how teams collaborate.

## Decision

Introduce a two-layer history model:

```
Messages          → working directory (live conversation state)
Checkpoints       → automatic, hidden autosaves
Commits           → manual, intentional milestones
Branches          → independent conversation lineages (Sprint 15)
```

### Hierarchy

```
Workspace
  Conversation
    Messages
    Checkpoints (automatic)
    Commits (manual)
    Branches
```

### Checkpoints

- Created automatically after every successful assistant message persist
- Point at `latest_message_id`
- Form a parent chain via `parent_checkpoint_id`
- Immutable and never exposed as a primary user action
- Exist for future recovery, replay, streaming recovery, rollback, and merge

### Commits

- Created only via explicit user action (`POST /conversations/{id}/commit`)
- Point at a checkpoint whose `latest_message_id` matches the selected message
- Parent commit is the latest commit in that conversation
- Identified by a short Git-like hash (first 7 characters of SHA-256 over conversation, checkpoint, parent, and timestamp)
- Immutable after creation

### Why commits are manual

Automatic commits would:

1. Flood history with low-signal entries
2. Blur the distinction between “AI answered” and “team agreed this is a milestone”
3. Make future merge/review UX harder to reason about

Manual commits preserve human intent. Checkpoints preserve machine-recoverable continuity.

## Consequences

### Positive

- Clear foundation for rollback, compare, merge requests, and IDE integration
- Backward compatible: existing conversations receive one initial checkpoint via migration, no automatic commits
- Reuses existing execution metadata for commit range summaries (provider, model, routing, credits, borrow)

### Negative / deferred

- Rollback, cherry-pick, and merge are intentionally not implemented in this sprint
- Checkpoints for historical assistant messages before migration are not fully reconstructed; only the latest message is backfilled

## Alternatives considered

1. **Commit on every message** — rejected as noisy and non-Git-like for collaboration
2. **Snapshots as full message copies** — rejected as storage-heavy; message IDs already provide ordering
3. **Reuse branch metadata only** — insufficient for intra-conversation milestones
