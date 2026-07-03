# Commit Model

## Status

**Implemented** (foundation). Rollback, cherry-pick, and merge are **not** implemented.

## Overview

```
Messages          → working directory
Checkpoints       → automatic autosaves
Commits           → manual milestones
```

Commits are intentional, immutable milestones with Git-like short hashes.

## Implemented

- Automatic checkpoints after each successful assistant message
- Manual commits via `POST /conversations/{id}/commit`
- Parent commit linkage (DAG within a conversation)
- Commit history UI, deep links, and commit graph visualization
- Range metadata (providers, credits, borrow) derived from existing execution data

See [ADR-011-conversation-commits.md](ADR-011-conversation-commits.md).

## Future

- Rollback to a commit (**Planned** / research track)
- Cherry-pick (**Not planned in v1**)
- Conversation merge (**Research**, v2.0)
- Semantic context restore from commits (**Research**, v2.0)

Never treat future items as shipped.
