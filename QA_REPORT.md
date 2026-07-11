# ConvHub QA Report — Beta Production-Readiness Audit

**Role:** QA Lead  
**Scope:** Full codebase audit (backend, frontend, Claude plugin)  
**Date:** 2026-07-11  
**Release target:** First shared beta (`0.1.0`)  
**Constraint:** Architecture unchanged; no feature work unless a critical bug is found during testing.

> **Follow-up (Documentation Sprint 1):** Product README, roadmap, architecture docs, plugin guide, and landing copy were aligned with MVP through Sprint 36. Deployment blocker **D2** (docs drift) is addressed; security and frontend-test blockers remain.

---

## Executive verdict

ConvHub is **conditionally ready for a closed beta** with known operators (self-hosted, trusted users), **not** ready for an open public beta.

| Area | Rating | Notes |
|------|--------|-------|
| Core collaboration (auth, workspaces, projects, chat, branch, commit, restore) | Strong | Broad backend pytest coverage |
| Credits / routing / borrowing | Strong for MVP | Pricing stubs remain |
| Repository / sync / memory / pull package / Claude handoff | Functional | Documented in MVP README / roadmap |
| Claude plugin push/pull | Functional MVP | Config footguns; silent hook failures |
| Frontend quality gates | Weak | **Zero** frontend automated tests |
| Security hardening | Weak for public beta | Default secrets, no rate limits |
| Ops / deploy | Adequate for demo | Compose defaults are development-oriented |

**Go / No-Go for closed beta:** **GO** if Release Checklist blockers are cleared.  
**Go / No-Go for public beta:** **NO-GO** until secrets, CORS, rate limiting, and frontend smoke tests are addressed.

---

## 1. User-facing feature inventory

### 1.1 Account & workspace

- Register / login / refresh / logout
- Workspace create, rename, delete
- Member invite (email + link), accept invite
- Role gates: owner / admin / member

### 1.2 Projects & conversations

- Project CRUD, archive/restore
- Conversation create, archive/restore, rename
- Participants invite
- Messages (send via chat gateway)
- Realtime streaming + presence (WebSocket)

### 1.3 Branching & memory artifacts

- Conversation branching from messages
- Manual commits + checkpoints
- Context Packages (view/export/restore)
- Branch manager, commit graph, overview, timeline, stats, compare
- Commit deep links

### 1.4 Providers, budget, sharing

- Personal (+ workspace) AI accounts; connection test
- Ownership-first routing policy
- Credit budget + ledger history
- Borrowing / lending preferences
- Hard budget enforcement on chat

### 1.5 Coding repository workspace

- Repository CRUD + branches
- Enable coding / attach-detach repository
- Sync status / push / pull metadata
- Branch Memory + history export
- Repository Memory (view/export)
- Pull Package (view/export)
- Claude Handoff preview/download
- Active developer workspace sessions
- External AI Sessions + transcript snapshot download
- Workspace Client protocol status

### 1.6 Claude Code plugin

- Hooks: SessionStart, PostToolUse, Stop, PreCompact, SessionEnd
- CLI: `convhub push`, `convhub pull`
- Local config `~/.convhub/config.json` + state `~/.convhub/state.json`

### 1.7 Admin / demo

- System health page (owner/admin)
- Demo toolkit (when `DEMO_MODE` enabled)
- Settings: routing + budget toggles (owner/admin)

---

## 2. Automated test posture

| Layer | Suites | Assessment |
|-------|--------|------------|
| Backend | ~42 `test_*.py` files | Good domain coverage for API/integration |
| Claude plugin | 18 pytest cases | Good for MVP hooks + push/pull |
| Frontend | **0** unit/e2e tests | Highest release risk for regressions |
| Cross-layer E2E | None (Playwright/Cypress absent) | Manual only |

Backend pytest is the primary safety net. Frontend changes can ship broken UX without CI signal beyond `tsc` + lint + build.

---

## 3. Security findings

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| S1 | **Critical** (public deploy) | Compose defaults ship `JWT_SECRET_KEY` and Fernet key placeholders | Require unique secrets; fail boot if defaults detected in `APP_ENV=production` |
| S2 | **High** | No API rate limiting on auth or chat | Add rate limits on `/auth/*` and `/chat/send` before public beta |
| S3 | **High** | `DEBUG=true` default in compose | Default `false` for non-dev profiles; disable OpenAPI outside debug |
| S4 | **Medium** | WebSocket auth via `?token=` query string | Prefer `Sec-WebSocket-Protocol` / first-message auth; scrub proxy logs |
| S5 | **Medium** | CORS origins easy to misconfigure | Document required origins; reject `*` with credentials |
| S6 | **Medium** | Invitation preview is unauthenticated | Keep, but rate-limit token probing |
| S7 | **Low** | AI provider credentials encrypted at rest (good) | Ensure key rotation runbook exists |
| S8 | **Low** | Plugin stores long-lived `api_token` in `~/.convhub/config.json` | Document file permissions (`0600`); prefer short-lived tokens later |

Workspace isolation via `X-Workspace-ID` + membership checks is generally sound and covered by many tests.

---

## 4. Race conditions & concurrency

| ID | Severity | Scenario | Notes |
|----|----------|----------|-------|
| R1 | **Medium** | Concurrent transcript uploads to same External AI Session | Offset/sequence checks are optimistic; unique `(session, sequence)` helps but dual clients can 409; no row lock |
| R2 | **Medium** | Concurrent `convhub push` + hook Stop flush | Same offset contention → 409; plugin may leave dirty state |
| R3 | **Medium** | Credit consume under concurrent chat sends | Budget tests exist; confirm DB-level atomic debit under load |
| R4 | **Low** | Realtime presence manager uses in-process `asyncio.Lock` | Breaks across multiple backend replicas (single-instance assumption) |
| R5 | **Low** | Repository Memory rebuild hooks after attach/commit | Best-effort rebuild; concurrent rebuilds can race version bumps |
| R6 | **Low** | Plugin SessionEnd disconnect failure still clears local session id | Server session may remain ACTIVE |

---

## 5. Deployment blockers

| ID | Blocker | Must fix before shared beta? |
|----|---------|------------------------------|
| D1 | Default JWT/Fernet secrets in compose | **Yes** |
| D2 | README/roadmap omit repos, sync, plugin, handoff (docs lie) | **Resolved** (Documentation Sprint 1) |
| D3 | Frontend has no smoke E2E in CI | Strongly recommended |
| D4 | Multi-replica realtime not supported | Document single-instance limit |
| D5 | Migrations head `033` — operators must run alembic | Document in release notes |
| D6 | Plugin starter config uses `REPLACE_WITH_*` placeholders that pass presence validation | Document first-run clearly |
| D7 | PromptBuilder stubs omit repo/memory context in chat | Accept as known limitation for beta |

---

## 6. Plugin edge cases (summary)

See also `KNOWN_LIMITATIONS.md`.

- Missing/invalid config → CLI fails loudly; hooks fail silently (stderr, exit 0)
- Placeholder UUIDs look “configured” but API 404/403
- Transcript truncate/rotate can clamp offset and skip bytes
- PostToolUse never uploads (by design) — relies on Stop/PreCompact/push
- Pull overwrites `~/Downloads/convhub-handoff.md`
- Push success text claims artifacts “updated” after GET refresh (not a write rebuild guarantee for all artifacts)

---

## 7. Critical bugs found during audit

**No P0 application crash bugs were reproduced in this audit pass.**  
Issues classified as release risks / gaps rather than confirmed production outages.

Highest priority fixes before open beta (not architecture changes):

1. Reject default secrets in production boot  
2. Rate-limit auth + chat  
3. ~~Align README with coding-workspace + plugin reality~~ (Documentation Sprint 1)  
4. Add minimal frontend Playwright smoke (login → conversation → send)

---

## 8. Deliverables in this audit package

| Document | Purpose |
|----------|---------|
| `QA_REPORT.md` | This executive audit |
| `TEST_MATRIX.md` | End-to-end + manual + missing automated coverage matrix |
| `KNOWN_LIMITATIONS.md` | Explicit beta boundaries |
| `RELEASE_CHECKLIST.md` | Go/No-Go checklist for operators |

---

## 9. Suggested beta cohorts

1. **Closed alpha:** 2–5 developers, single workspace, demo mode optional, Claude plugin optional  
2. **Closed beta:** Multiple workspaces, real providers, plugin push/pull exercised weekly  
3. **Public beta:** Only after S1–S3, D2–D3, and frontend smoke CI are green
