# ConvHub Release Checklist — First Beta

Use this checklist before announcing a beta build.  
Tier: choose **Closed beta** or **Public beta** and meet that column’s bar.

| Item | Closed beta | Public beta | Owner | Status |
|------|-------------|-------------|-------|--------|
| **Secrets** | | | | |
| Unique `JWT_SECRET_KEY` (≥32 chars) set | Required | Required | Ops | ☐ |
| Unique `CREDENTIALS_ENCRYPTION_KEY` set | Required | Required | Ops | ☐ |
| Postgres password not `postgres`/`postgres` | Recommended | Required | Ops | ☐ |
| Demo mode off unless intentional | Required | Required | Ops | ☐ |
| `DEBUG=false`, OpenAPI disabled | Recommended | Required | Ops | ☐ |
| **Configuration** | | | | |
| `CORS_ORIGINS` matches real frontend origin(s) | Required | Required | Ops | ☐ |
| `DATABASE_URL` points at dedicated DB | Required | Required | Ops | ☐ |
| `alembic upgrade head` → revision **033** | Required | Required | Ops | ☐ |
| Frontend built with correct `VITE_API_URL` | Required | Required | Ops | ☐ |
| **Quality gates** | | | | |
| `cd backend && pytest` green | Required | Required | Eng | ☐ |
| `cd plugins/claude && pytest` green | Required | Required | Eng | ☐ |
| `cd frontend && npm run build` green | Required | Required | Eng | ☐ |
| `cd frontend && npm run lint` green | Required | Required | Eng | ☐ |
| Frontend Playwright smoke in CI | Optional | Required | Eng | ☐ |
| **Security** | | | | |
| Boot rejects default JWT secret in production | Optional | Required | Eng | ☐ |
| Rate limit `/auth/*` and `/chat/send` | Optional | Required | Eng | ☐ |
| HTTPS terminated (TLS) | Recommended | Required | Ops | ☐ |
| Backup / restore procedure documented | Recommended | Required | Ops | ☐ |
| **Docs** | | | | |
| README “Implemented today” includes repos/sync/plugin | Required | Required | Eng | ☑ |
| Roadmap statuses updated for coding-workspace + Claude MVP | Required | Required | Eng | ☑ |
| `KNOWN_LIMITATIONS.md` linked from README | Recommended | Required | Eng | ☑ |
| Plugin README first-run config steps verified | Required | Required | Eng | ☐ |
| **Manual QA sign-off** (`TEST_MATRIX.md`) | | | | |
| E01–E07 core collaboration | Required | Required | QA | ☐ |
| E08–E13 repository / memory / handoff | Required | Required | QA | ☐ |
| E14 plugin push/pull on real Claude Code | Required if plugin advertised | Required | QA | ☐ |
| E15 realtime two-browser | Recommended | Required | QA | ☐ |
| M-ISO workspace isolation spot checks | Required | Required | QA | ☐ |
| M-BUD hard enforcement spot check | Recommended | Required | QA | ☐ |
| **Plugin packaging** | | | | |
| `install.sh` / `uninstall.sh` verified on clean machine | Required if shipping plugin | Required | QA | ☐ |
| `convhub` on PATH (`~/.local/bin`) | Required if shipping plugin | Required | QA | ☐ |
| No placeholder tokens in shared config samples | Required | Required | Eng | ☐ |
| **Runtime assumptions acknowledged** | | | | |
| Single backend replica for realtime | Required | Required | Ops | ☐ |
| No Git automation expected by users | Required | Required | PM | ☐ |
| **Go decision** | | | | |
| QA Lead sign-off | Required | Required | QA | ☐ |
| Eng Lead sign-off | Required | Required | Eng | ☐ |

---

## Pre-flight commands

```bash
# Backend tests
cd backend && PYTHONPATH=. python -m pytest -q

# Plugin tests
cd plugins/claude && python -m pytest tests -q

# Frontend
cd frontend && npm run lint && npm run build

# Migrations (running stack)
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

---

## Release notes template (fill at ship)

- **Version:** 0.1.0-beta.X  
- **Included:** (core collab + coding workspace + Claude plugin MVP — yes/no)  
- **Not included:** Git automation, other IDE plugins, OAuth, summarization  
- **Breaking:** migration to 033 required  
- **Known issues:** link `KNOWN_LIMITATIONS.md`  
- **Upgrade:** `alembic upgrade head`; rebuild frontend with `VITE_API_URL`

---

## Sign-off

| Role | Name | Date | Tier (Closed / Public) | Decision |
|------|------|------|------------------------|----------|
| QA Lead | | | | GO / NO-GO |
| Eng Lead | | | | GO / NO-GO |
| Ops | | | | GO / NO-GO |
