# Contributing to ConvHub

Thank you for helping improve ConvHub!

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
feat: add system health page for workspace admins
fix: map 402 errors to friendly credit messages
docs: expand architecture diagrams for realtime events
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

## Questions

Open a [Question issue](.github/ISSUE_TEMPLATE/question.md) if you are unsure about approach or scope.
