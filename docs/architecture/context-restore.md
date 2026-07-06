# Context Restore (Project Checkpoints)

## Status

**Implemented** (Sprint 20)

## Overview

Context Restore is the Git-checkout equivalent for project memory.

```
Context Package (immutable snapshot)
        ↓
Restore
        ↓
New working conversation
```

History is never rewritten. Restore always creates a **new** conversation with lineage metadata pointing back to the source package, commit, and conversation.

## Implemented

- Restore metadata on `Conversation`:
  - `restored_from_package_id`
  - `restored_from_commit_id`
  - `restored_from_conversation_id`
  - `restored_by_user_id`
  - `restored_at`
- `POST /context-packages/{id}/restore`
- `GET /conversations/{id}/restore-info`
- Options:
  - restore participants (or only self)
  - restore messages from package snapshot
  - restore branch metadata (name only; no parent branch attachment)
  - restore into the original project (default) or another project in the workspace
- UI: Restore dialog, Restored badge, header lineage link, sidebar distinction

## Not restored

- AIRequest rows
- Borrow records
- Credit transactions
- Realtime events

## Guarantees

- Original conversation unchanged
- Context Package remains immutable
- Multiple restores from the same package are allowed
- Restored conversation behaves as a normal conversation afterward
