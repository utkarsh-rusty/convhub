# ConvHub Test Matrix — Beta

Complete end-to-end coverage map for first beta.  
**Legend:** `Auto` = automated exists · `Gap` = missing automated · `Manual` = required human QA · `N/A` = out of beta scope

---

## A. End-to-end journeys (product)

| ID | Journey | Happy path | Negative / edge | Auto | Manual |
|----|---------|------------|-----------------|------|--------|
| E01 | New user onboarding | Register → create workspace → create project → create conversation | Duplicate email; weak password | Partial (`test_api_auth`, projects) | **Required** |
| E02 | Invite teammate | Owner invites → invitee accepts → appears in members | Expired/invalid token; non-member access | Partial (`test_api_workspaces`) | **Required** |
| E03 | Connect provider & chat | Add Anthropic/OpenAI account → test → send message → stream reply | Invalid key; provider down; insufficient credits | Partial (accounts, gateway, budget) | **Required** live providers |
| E04 | Borrowing path | User A exhausted → borrow from B → chat succeeds → ledger shows | Share disabled; reserved credits | Partial (`test_resource_sharing`, budget API) | **Required** |
| E05 | Branch & commit | Message → branch → commit → context package created | Non-owner commit; empty branch | Strong | Spot-check UI |
| E06 | Restore context | Restore package → new conversation seeded | Restore without access | Strong (`test_context_restore`) | Spot-check UI |
| E07 | Branch visualization | Overview / manager / graph / timeline / compare / stats | Large graphs; archived branches | Strong backend | **Required** UI |
| E08 | Enable coding workspace | Enable coding → attach repo → branch memory updates | Detach; disable coding | Strong | **Required** |
| E09 | Sync metadata | Sync status → push → pull | Detached branch; conflict states | Strong (`test_sync_api`) | Spot-check UI |
| E10 | Repository Memory | Branch create → memory generated → export md/json | Empty repo | Strong | Spot-check UI |
| E11 | External AI session | Connect → upload chunks → snapshot → disconnect | Bad offsets; cross-workspace | Strong | Plugin path **Required** |
| E12 | Pull Package | Generate JSON/MD with memory + commit + transcript | Empty vs full repo | Strong | Spot-check UI |
| E13 | Claude Handoff | GET handoff markdown; UI preview/download | Permissions 404 | Strong | **Required** |
| E14 | Plugin push/pull | Hook session → dirty → push → pull handoff file | Missing config; closed session; repeat push | Plugin auto (18) | **Required** on real Claude Code |
| E15 | Realtime collab | Two browsers same conversation → stream + presence | Token expiry mid-WS | Partial (`test_realtime`) | **Required** |
| E16 | Demo mode | Seed users → login as Alice → toolkit actions | Demo disabled → 404 | Partial | Optional |
| E17 | Admin settings | Routing policy + hard budget toggles | Member cannot edit | Partial | Spot-check |

---

## B. Manual QA cases (release suite)

### B1 — Auth & session

| Case | Steps | Expected |
|------|-------|----------|
| M-AUTH-01 | Register new user | 201; can login |
| M-AUTH-02 | Login wrong password | Error toast; no token |
| M-AUTH-03 | Wait for access expiry / force 401 | Silent refresh or redirect `/login` |
| M-AUTH-04 | Logout | Tokens cleared; protected routes redirect |

### B2 — Workspace isolation

| Case | Steps | Expected |
|------|-------|----------|
| M-ISO-01 | User in WS-A requests resource ID from WS-B | 403/404 |
| M-ISO-02 | Omit `X-Workspace-ID` on API | 422/401 as designed |
| M-ISO-03 | Member cannot PATCH workspace budget settings | 403 |

### B3 — Conversation core

| Case | Steps | Expected |
|------|-------|----------|
| M-CHAT-01 | Send message with valid provider | Assistant streams; message persisted |
| M-CHAT-02 | Non-participant opens conversation | Read-only UI |
| M-CHAT-03 | Search message; open `?message=` deep link | Scrolls/highlights |
| M-CHAT-04 | Commit milestone | Commit + package appear in history |

### B4 — Repository / plugin workflow

| Case | Steps | Expected |
|------|-------|----------|
| M-REPO-01 | Create repository + default branch | Memory card populated |
| M-REPO-02 | Attach conversation to repo | Sync + memory regenerate |
| M-REPO-03 | Preview Claude Handoff on repo page | Dialog shows markdown sections |
| M-PLUG-01 | Install plugin; configure real IDs | Hooks present in Claude settings |
| M-PLUG-02 | Start Claude session in repo | Session appears under External AI Sessions |
| M-PLUG-03 | Use tools then `convhub push` | Success checklist; offset advances |
| M-PLUG-04 | `convhub pull` | File at `~/Downloads/convhub-handoff.md` |
| M-PLUG-05 | Paste handoff into new Claude session | Manual continuation works |
| M-PLUG-06 | Repeat push with no new transcript | Success; no duplicate chunk |
| M-PLUG-07 | Uninstall plugin | Hooks removed; other hooks preserved |

### B5 — Budget & failure UX

| Case | Steps | Expected |
|------|-------|----------|
| M-BUD-01 | Exhaust credits with hard enforcement | Chat blocked with clear error |
| M-BUD-02 | Kill API mid-page load on Dashboard | Should not look like “no projects” forever — **known gap** |
| M-BUD-03 | Demo toolkit reset credits | Balances update |

---

## C. Automated coverage by domain

| Domain | Existing auto | Priority gaps to add |
|--------|---------------|----------------------|
| Auth | `test_api_auth` | Brute-force / refresh reuse after logout |
| Workspaces | `test_api_workspaces` | Concurrent invite accept |
| Projects | `test_projects` | — |
| Conversations | `test_api_conversations`, branching, ownership | — |
| Commits / packages / restore | Multiple | — |
| Visualization | `test_branch_visualization`, manager | — |
| Budget / sharing / routing | Multiple | Load test concurrent debit |
| Repositories / coding | Multiple | — |
| Sync / sessions / client | Multiple | Multi-client heartbeat expiry |
| External AI / snapshot / pull / handoff | Multiple | Concurrent upload 409 path asserted under load |
| Claude plugin | 18 tests | Hook stderr failure surfacing; transcript shrink |
| Frontend | **None** | Playwright smoke: login, chat, repo handoff buttons |
| Realtime | `test_realtime` | Multi-worker presence |
| Demo / system | sprint12/13, demo | — |

---

## D. Missing automated tests (recommended backlog)

### P0 — before public beta

1. **Frontend Playwright smoke** (login → create conversation → send mock provider message)  
2. **Frontend Playwright** repository page: open Pull Package + Claude Handoff preview  
3. **Auth rate-limit test** (once middleware exists)  
4. **Production settings guard test** (boot fails on default JWT secret when `APP_ENV=production`)

### P1 — closed beta hardening

5. Concurrent external AI upload → expect one 201 and one 409  
6. Plugin: transcript file truncated below `last_uploaded_offset`  
7. Plugin: push when remote session already `closed`  
8. WebSocket reconnect after access token refresh  
9. Frontend empty-vs-error distinction on Dashboard/Members/Budget query failure  
10. Invite flow: unauthenticated user hitting `/invite/:token` (login bounce then return)

### P2 — quality

11. Visual regression on conversation + graph pages  
12. Accessibility smoke (keyboard nav, dialog focus trap)  
13. docker-compose fresh install scripted smoke  
14. Migration upgrade/downgrade pair for latest 2 revisions

---

## E. Test environments

| Env | Purpose |
|-----|---------|
| Local compose + `convhub_test` DB | Backend pytest |
| Local frontend `npm run dev` | Manual UI |
| Claude Code + plugin hooks | Plugin E2E |
| Staging with rotated secrets | Pre-release sign-off |

**Seed users (demo):** per README when `DEMO_MODE=true`.

---

## F. Exit criteria for beta test pass

- All **E01–E15** manual cases executed once on staging  
- Backend `pytest` green on CI / local against `convhub_test`  
- Plugin `pytest` green  
- Frontend `npm run build` + `npm run lint` green  
- No open **Critical/High** security items from `QA_REPORT.md` for the chosen beta tier
