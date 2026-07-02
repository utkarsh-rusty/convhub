# ConvHub

Shared AI workspace for development teams — collaborate on conversations, route across providers, share credits, and see updates in real time.

> Screenshots: add `docs/images/` captures of the dashboard, conversation view, and system health page.

## Features

- **Team workspaces** with roles (owner, admin, member)
- **Shared conversations** with participants, typing indicators, and live messages
- **AI gateway** with provider abstraction (Anthropic, OpenAI, Gemini, Groq, Ollama, Mock)
- **Routing engine** with multiple policies (priority, balanced, cheapest, …)
- **Credit ledger** with monthly budgets and enforcement
- **Resource sharing & borrowing** between teammates
- **Realtime collaboration** via WebSockets (streaming AI, presence, live dashboard)
- **Demo mode** for instant try-it-out logins (Alice, Bob, Charlie)

## Architecture

```
Browser (React) ──REST/WebSocket──▶ FastAPI API
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              PostgreSQL        AI Providers      Routing / Credits
```

See [docs/architecture/](docs/architecture/) for flow diagrams and ADRs.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend dev)

### 1. Clone and configure

```bash
git clone https://github.com/utkarsh-rusty/convhub.git
cd convhub
cp backend/.env.example backend/.env
```

### 2. Start backend + database

```bash
docker compose up --build
```

API: http://localhost:8000/docs

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

## Demo Mode

Enable demo toolkit and one-click logins:

```env
# backend/.env
DEMO_MODE=true
# or ENABLE_DEMO_MODE=true
```

Seed demo users and workspace:

```bash
cd backend && PYTHONPATH=.. python ../scripts/seed_demo.py
```

Recreate backend to pick up env changes:

```bash
docker compose up -d --force-recreate backend
```

On the login page you will see **Continue as Alice / Bob / Charlie** (password is managed server-side).

Demo users share password `demo12345` if signing in manually with seeded emails.

## Testing

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

See [roadmap.md](roadmap.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
