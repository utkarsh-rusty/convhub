# ConvHub

**GitHub for AI Conversations.**

ConvHub is a collaborative AI workspace where teams can build, share, and continue AI conversations together while every user keeps ownership of their own AI providers.

```
Developer A (Claude)
Developer B (OpenAI)
Developer C (Groq)
        ↓
Shared Conversation
        ↓
Realtime Collaboration
        ↓
Ownership-first Routing
        ↓
Assistant Responses
```

## Features

### Collaboration

- Shared conversations
- Multiple participants
- Live collaboration
- Presence
- Typing indicators
- Conversation permissions

### AI Orchestration

- Multi-provider support
- Ownership-first routing
- Automatic provider failover
- Borrowing between conversation participants
- Local models via Ollama

### Governance

- Workspace budgets
- Credit ledger
- Borrow limits
- Routing policies
- AI account ownership

### Realtime

- WebSockets
- Streaming responses
- Live credit updates
- Live routing events

### Enterprise

- JWT authentication
- Workspace isolation
- Role-based permissions
- Audit trail
- Provider abstraction

## Architecture

```
Workspace
        ↓
Conversation
        ↓
Participants
        ↓
Prompt Builder
        ↓
Ownership-first Routing
        ↓
Sender Providers
        ↓
Borrow Engine (only when needed)
        ↓
LLM Provider
        ↓
Assistant Message
        ↓
Realtime Broadcast
```

| Layer | Role |
|-------|------|
| **Workspace** | Team boundary for members, roles, budgets, and settings. |
| **Conversation** | Shared thread where participants collaborate on messages and context. |
| **Participants** | Users in the conversation; borrowing is limited to this group. |
| **Prompt Builder** | Assembles conversation history and policy into a provider-ready prompt. |
| **Ownership-first Routing** | Routes each message through the sender's own AI accounts first. |
| **Sender Providers** | The sender's configured providers (Claude, GPT, Groq, Gemini, Ollama, …). |
| **Borrow Engine** | When the sender has no usable provider, borrows from an eligible participant. |
| **LLM Provider** | Executes the request through the selected account and streams the response. |
| **Assistant Message** | Persists the reply and execution metadata for the conversation. |
| **Realtime Broadcast** | Pushes messages, presence, credits, and routing events to connected clients. |

See [docs/architecture/](docs/architecture/) for diagrams, flow notes, and ADRs.

## Project Structure

```
convhub/
├── backend/
│   ├── app/
│   │   ├── ai/                 # AI orchestration, providers, prompt builder
│   │   ├── ai_accounts/        # Per-user provider accounts
│   │   ├── auth/               # JWT authentication
│   │   ├── conversations/    # Conversations, messages, participants
│   │   ├── demo/               # Demo mode toolkit
│   │   ├── realtime/           # WebSocket events and streaming
│   │   ├── resource_management/# Budgets and credit ledger
│   │   ├── resource_sharing/   # Borrow engine and lending preferences
│   │   ├── routing/            # Ownership-first routing engine
│   │   ├── system/             # Health and workspace diagnostics
│   │   └── workspaces/         # Workspaces, members, invitations
│   ├── alembic/                # Database migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/         # UI components (conversation, layout, landing)
│       ├── context/            # Auth and workspace state
│       ├── hooks/              # Realtime and theme hooks
│       ├── lib/                # API client and utilities
│       └── pages/              # App and landing pages
├── docs/
│   └── architecture/           # Architecture overview and ADRs
├── scripts/                    # Demo seed and utilities
├── docker-compose.yml
├── CONTRIBUTING.md
└── roadmap.md
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend development)

### 1. Clone and configure

```bash
git clone https://github.com/utkarsh-rusty/convhub.git
cd convhub
cp backend/.env.example backend/.env
```

### 2. Start backend and database

```bash
docker compose up --build
```

API docs: http://localhost:8000/docs

### 3. Run migrations (first time)

```bash
docker compose exec backend alembic upgrade head
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### Demo mode

Enable one-click demo logins:

```env
# backend/.env
DEMO_MODE=true
```

Seed demo users and workspace:

```bash
cd backend && PYTHONPATH=.. python ../scripts/seed_demo.py
docker compose up -d --force-recreate backend
```

On the login page you will see **Continue as Alice / Bob / Charlie**.

### Testing

```bash
cd backend
python -m pytest
```

```bash
cd frontend
npm run build
npm run lint
```

## Roadmap

### Phase 1 (Completed)

- Authentication
- Workspaces
- Shared conversations
- AI providers
- Ownership routing
- Borrow engine
- Credits
- Realtime collaboration

### Phase 2 (Next)

- Conversation branching
- Fork conversations
- Merge conversations
- Timeline
- Snapshots

### Phase 3

- Import ChatGPT conversations
- Import Claude conversations
- Import Gemini conversations
- Markdown import/export

### Phase 4

- Knowledge packs
- Files
- Search
- Shared context
- Long-term memory

### Phase 5

- Enterprise SSO
- Analytics
- Audit dashboard
- Billing
- Team administration

See [roadmap.md](roadmap.md) for details.

## Contributing

Contributions are welcome. ConvHub is in **early beta** — issues, docs improvements, and pull requests help shape the project.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
