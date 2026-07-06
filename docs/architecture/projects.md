# Projects

## Status

**Implemented** (Sprint 21)

## Overview

Projects are the permanent home for project memory.

```
Workspace
    ↓
Projects
    ↓
Conversations
    ↓
Branches
    ↓
Commits
    ↓
Context Packages
```

Projects inherit workspace permissions. There are no project-specific roles.

## Implemented

- First-class `projects` table with name, description, icon, color, creator, archive support
- Required `conversation.project_id`
- Automatic **Default Project** per workspace (migration + workspace creation)
- CRUD APIs, archive/restore, delete only when empty
- Project overview page (repo-style home)
- Sidebar hierarchy: Workspace → Projects → Conversations
- Conversation creation and Context Restore target a project

## Future attachment points

Projects are designed to become the attachment point for:

- Git repositories
- IDE integrations
- Context Libraries
- Knowledge Graphs
- AI Coding Sessions
