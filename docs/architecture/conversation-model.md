# Conversation Model

## Status

**Implemented**

## Overview

A conversation is the primary unit of collaborative AI work in ConvHub.

```
Workspace
  └── Conversation
        ├── Participants
        ├── Messages (working directory)
        ├── Checkpoints (automatic)
        ├── Commits (manual)
        └── Branches (child conversations)
```

## Implemented

- Conversations belong to a workspace
- Each conversation has an owner and participants
- Messages form the live working directory
- Non-participants may view branches read-only (workspace members)
- Participants can chat, branch, and commit
- Owners can invite, remove, rename, and archive

See also [conversation-lifecycle.md](conversation-lifecycle.md).

## Future

- First-class Projects containing conversations (**Planned**, v1.2)
- Conversation merge (**Research**, v2.0)

Not implemented.
