# ConvHub Architecture

ConvHub helps teams collaborate on AI-assisted software development: shared conversations, versioned project memory, and Claude Code handoff — while each participant keeps ownership of their own AI providers.

See [architecture/architecture-overview.md](architecture/architecture-overview.md) for the end-to-end flow.

## Core Principles

### 1. Workspace owns collaboration

Users collaborate inside Workspaces.

### 2. Conversations carry team knowledge

Messages, commits, and branches capture how the team thinks — not only what code changed.

### 3. Messages are the working directory

Commits are manual milestones. Checkpoints are automatic.

### 4. AI providers are interchangeable

No conversation is tied to Claude, GPT, or Gemini.

### 5. Ownership-first routing

Senders use their own providers first. Borrowing is participant-scoped.

### 6. Budgets are separate from conversations

Credits govern sharing; they do not replace provider ownership.

### 7. Git for code; ConvHub for AI context

`git push` / `git pull` version source. `convhub push` / `convhub pull` move AI collaboration context.

### 8. Modular monolith first

Microservices only when necessary.

## Implemented vs planned

| Area | Status |
|------|--------|
| Conversations, commits, branches | **Implemented** |
| Context Packages & Context Restore | **Implemented** |
| Ownership routing & borrowing | **Implemented** |
| Realtime | **Implemented** |
| Budgets & credits | **Implemented** |
| Coding repositories & Repository Memory | **Implemented** |
| External AI Sessions & Transcript Snapshots | **Implemented** |
| Pull Package & Claude Handoff | **Implemented** |
| Claude Code plugin (`convhub push` / `pull`) | **Implemented** |
| Remote Git automation | **Planned** |
| VS Code / Codex / Gemini / Cursor adapters | **Planned** |
| Semantic merge / knowledge graph | **Research** |
