# ADR-014: First-class Projects

## Status

Accepted — Sprint 21 · **Implemented**

## Context

Conversations, commits, and context packages need a durable container that can later attach Git repositories, IDE sessions, and knowledge graphs. Workspaces alone are too broad.

## Decision

Introduce **Projects** as a first-class domain object between Workspace and Conversation:

1. Every workspace has at least one **Default Project**
2. Every conversation belongs to exactly one project (`project_id` required)
3. Projects inherit workspace membership permissions
4. Empty projects may be deleted; projects with conversations may not
5. Context Restore may target the original project or another project in the same workspace

## Consequences

### Positive

- Clear permanent home for project memory
- Additive migration with no data loss
- Future Git/IDE features have a natural attachment point

### Deferred

- Project-specific permissions
- Git repository linkage
- Project-level knowledge graphs
