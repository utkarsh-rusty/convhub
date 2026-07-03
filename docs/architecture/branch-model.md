# Branch Model

## Status

**Implemented** (branching and visualization). Merge is **not** implemented.

## Overview

Branches are independent conversations forked from a parent message.

```
Main
├── Feature A
│   ├── Experiment 1
│   └── Experiment 2
└── Alternative Ending
```

## Implemented

- Branch from any message (`POST /conversations/{id}/branch`)
- Branch owner = branch creator; participants start as creator only
- Parent linkage (`parent_conversation_id`, `branch_from_message_id`, `branch_name`)
- Branch manager, overview, commit graph, ahead/behind status (derived)
- Read-only access for workspace members who are not participants

## Future

- Conversation merge (**Research**, v2.0)
- Semantic merge assistant (**Research**, v2.0)

Not implemented.
