# ConvHub Known Limitations — Beta

Explicit boundaries for the first beta. These are **not** bugs by themselves; they are product/architecture constraints operators and testers must understand.

---

## Product scope

### Documented MVP (through Sprint 36)

Repository linkage, sync metadata, External AI Sessions, Transcript Snapshots, Pull Packages, Claude Handoff, and the Claude Code plugin (`convhub push` / `convhub pull`) are **implemented** and documented in the root [README.md](README.md) and [roadmap.md](roadmap.md).

### Not in beta (by design)

- Git automation (clone, commit, PR, branch sync with remotes)
- VS Code / Cursor / Codex / Gemini CLI plugins
- Automatic clipboard paste or prompt injection into Claude
- AI summarization of transcripts or repository memory
- Semantic restore, conversation merge, knowledge graph
- Decision-tracking product module (beyond memory text sections)
- OAuth for the Claude plugin (bearer token config only)

---

## AI / chat

- **PromptBuilder** still stubs richer context sections (repo memory, snapshots, pinned standards). Chat does not automatically inject Pull Package or Repository Memory.
- **Credit pricing** uses simplified policy; per-model / workspace plan rates are not fully applied (`credit_policy` TODOs).
- Provider behavior depends on user-supplied API keys; Mock provider is for tests/demo.

---

## Repository & sync

- Sync push/pull is **metadata orchestration** in ConvHub, not a full Git wire protocol.
- Workspace Client APIs are protocol foundations; a polished IDE client is not shipped.
- Repository Memory / Pull Package / Handoff are **deterministic compositions**, not LLM-written briefs.
- “Updated/refreshed” messaging on `convhub push` means ConvHub artifacts were **fetched/verified**, not that every artifact was rewritten.

---

## Claude plugin

- Observes Claude via **official hooks only**; does not scan `~/.claude/projects`.
- `PostToolUse` only marks dirty; uploads happen on Stop / PreCompact / `convhub push`.
- Hook failures are **non-blocking** (logged to stderr, exit 0) so Claude continues even if ConvHub is down.
- Local state lives in `~/.convhub/`; uninstall does not delete it.
- Starter `config.json` contains placeholder UUIDs/tokens that must be replaced.
- Pull always writes `convhub-handoff.md` (overwrite) under Downloads (or `CONVHUB_DOWNLOAD_DIR`).
- Transcript file truncation/rotation can cause offset clamp behavior; re-upload of skipped regions is not guaranteed.
- One machine identifier + branch combination resumes a single ACTIVE external session; multi-machine workflows need distinct identifiers.

---

## Frontend

- **No automated frontend tests**; regressions are caught by TypeScript build/lint and manual QA.
- Several list pages can render “empty” on API failure instead of an explicit error state.
- Invite links require authentication (`ProtectedRoute`); anonymous users are sent to login first.
- Default API URL is `http://localhost:8000/api/v1` unless `VITE_API_URL` is set.

---

## Realtime & scale

- Presence/realtime connection manager is **in-process**; multiple backend replicas will not share presence correctly.
- Beta assumption: **single backend instance** behind compose or a single VM.
- WebSocket authenticates via query `token` (operational logging caution).

---

## Security / ops (accepted for closed beta only)

- Development compose defaults include predictable JWT/Fernet secrets — **unacceptable for internet exposure**.
- No global API rate limiting yet.
- `DEBUG` may be true in local compose profiles.
- Demo mode, when enabled, exposes powerful admin simulation tools — disable on shared staging unless intentional.

---

## Data model / migrations

- Schema head: Alembic **033** (transcript snapshots). Fresh installs must run migrations.
- External AI transcript chunks are append-only; there is no transcript edit/redact UI.
- No soft-delete story for uploaded transcript content beyond session/repo cascading deletes.

---

## Testing gaps (accepted risk)

| Gap | Impact |
|-----|--------|
| Zero frontend e2e | UI regressions possible |
| No load tests | Credit/upload races under pressure unknown |
| Plugin not tested inside real Claude Code in CI | Hook payload drift possible across Claude versions |

---

## Support stance for beta

1. Prefer **closed** workspaces with known members.  
2. Rotate secrets before any shared URL.  
3. Treat Claude plugin as **opt-in power-user** tooling.  
4. File issues with: workspace role, repro steps, API status codes, plugin `state.json` offsets (redact tokens).
