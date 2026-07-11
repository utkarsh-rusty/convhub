# Contributing to ConvHub

Thank you for helping improve ConvHub!

ConvHub brings Git-style collaboration to AI-assisted software development: shared conversations, versioned project memory, and Claude Code handoff (`convhub push` / `convhub pull`) — while each person keeps ownership of their own AI providers. The project is in **early beta**; contributions to code, documentation, and issue triage are welcome.

## Local setup

1. Fork and clone the repository.
2. Copy `backend/.env.example` to `backend/.env`.
3. Start services: `docker compose up --build`.
4. Run migrations: `docker compose exec backend alembic upgrade head`.
5. Frontend: `cd frontend && npm install && npm run dev`.
6. Optional Claude plugin: see [plugins/claude/README.md](plugins/claude/README.md).

## Branch naming

- `feat/short-description` — new features
- `fix/short-description` — bug fixes
- `docs/short-description` — documentation only
- `chore/short-description` — tooling, deps, CI

## Commit style

Use clear, imperative subjects:

```
feat: add conversation branching UI
fix: show lender names in credit history
docs: refresh product positioning
```

## Running tests

```bash
cd backend
PYTHONPATH=. python -m pytest -q
```

Plugin:

```bash
cd plugins/claude
python -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm run lint && npm run build
```

## Code formatting

Backend:

```bash
cd backend
ruff check app tests
ruff format app tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Pull requests

- Keep PRs focused and reviewable.
- Ensure backend tests pass and frontend builds.
- Do not include secrets or `.env` files.
- Fill out the PR template.

## Documentation

- Describe **implemented** MVP behavior accurately (through Sprint 36).
- Separate **Complete**, **Planned**, and **Research** — never mark future work as shipped.
- Keep deep technical material under [docs/](docs/); keep the root README scannable in under three minutes.
- Canonical messaging: [README.md](README.md), [roadmap.md](roadmap.md), [docs/index.md](docs/index.md).

## Questions

Open a [Question issue](.github/ISSUE_TEMPLATE/question.md) if you are unsure about approach or scope.
