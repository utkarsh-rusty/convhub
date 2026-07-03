# Contributing to ConvHub

Thank you for helping improve ConvHub!

ConvHub is **GitHub for AI Conversations** — a collaborative AI workspace where teams share conversation threads while each person keeps ownership of their own providers. The project is in **early beta**; contributions to code, documentation, and issue triage are welcome.

## Local setup

1. Fork and clone the repository.
2. Copy `backend/.env.example` to `backend/.env`.
3. Start services: `docker compose up --build`.
4. Run migrations: `docker compose exec backend alembic upgrade head`.
5. Frontend: `cd frontend && npm install && npm run dev`.

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
docs: refresh landing page positioning
```

## Running tests

```bash
cd backend
python -m pytest
```

With coverage:

```bash
python -m pytest --cov=app
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

Positioning should describe ConvHub as **GitHub for AI Conversations**, not as an AI gateway or proxy. See [README.md](README.md) and [docs/](docs/) for the canonical messaging.

## Questions

Open a [Question issue](.github/ISSUE_TEMPLATE/question.md) if you are unsure about approach or scope.
