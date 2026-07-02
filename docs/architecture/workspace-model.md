# Workspace Model

```mermaid
erDiagram
    User ||--o{ WorkspaceMember : belongs_to
    Workspace ||--o{ WorkspaceMember : has
    Workspace ||--o{ Conversation : contains
    Workspace ||--o{ AIAccount : configures
    Workspace ||--|| WorkspaceBudgetSettings : has
    WorkspaceMember {
        uuid user_id
        uuid workspace_id
        enum role
    }
```

## Roles

| Role | Capabilities |
|------|------------|
| Owner | Full control, billing settings, delete workspace |
| Admin | Members, AI providers, routing, system health |
| Member | Conversations, own budget, sharing preferences |

## Context

Every authenticated workspace request includes `X-Workspace-ID`. Dependencies resolve `WorkspaceContext` (user + membership) before business logic runs.
