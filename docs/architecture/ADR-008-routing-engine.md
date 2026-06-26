# ADR-008: Routing Engine

## Status

Accepted — 2026-06-26

## Context

ConvHub workspaces can configure multiple `AIAccount` records (Anthropic, Ollama, Mock).
Sprint 9B added budget enforcement. The gateway previously called
`resolve_primary_active_account()` — a hard-coded priority sort that ignored workspace
routing preferences and could not evolve.

Requirements:

- Gateway must never choose accounts directly
- Workspace-configurable routing policies
- Auditable routing decisions on every `AIRequest`
- Preserve existing `AIAccount` CRUD and credential storage

## Decision

Introduce a **Routing Engine** between the gateway and provider factory:

```
Gateway → RoutingEngine.select(RoutingContext) → RoutingDecision → Provider Factory
```

### Components

| Component | Responsibility |
|-----------|----------------|
| `RoutingContext` | Workspace, user, conversation, cost estimate |
| `RoutingEngine` | Filter eligible accounts, invoke policy, return decision |
| `RoutingPolicy` | Score and rank candidates |
| `ProviderHealth` | Credential validation gate |
| `RoutingDecision` | Selected account, model, policy, score, reason |

### Pipeline

1. **Filter** — active accounts, valid credentials, local-model policy, optional provider hint
2. **Score** — policy-specific ranking (priority, spend, usage, cost)
3. **Rank** — policy selects lowest/best score
4. **Select** — return `RoutingDecision` with resolved model and credentials

### Policies

| Policy | Selection criteria |
|--------|-------------------|
| `OWNER_FIRST` | Owner → priority order; members → balanced spend |
| `BALANCED` | Lowest `monthly_spent` |
| `LOWEST_USAGE` | Lowest AI request cost this month |
| `CHEAPEST` | Ollama → Mock → paid providers |
| `PRIORITY` | Lowest `priority` field |

Workspace default: `OWNER_FIRST` (migration backfill).

### Gateway changes

- Replaced `resolve_primary_active_account()` with `RoutingEngine.select()`
- Persists on `AIRequest`: `selected_account_id`, `selected_policy`, `routing_policy`, `routing_reason`, `routing_score`
- Gateway never inspects account lists or priority fields

### API

- `GET /workspaces/{id}/routing` — policy, active accounts, selection preview
- `PATCH /workspaces/{id}/routing` — update policy (Owner/Admin)

## Why the gateway never chooses providers

- **Single responsibility** — gateway orchestrates prompts, budgets, and providers; routing is a distinct domain
- **Testability** — policies unit-test without HTTP or LLM calls
- **Auditability** — every request records why an account was chosen
- **Extensibility** — new policies (latency, region, model capability) plug into the engine without gateway changes

## Consequences

### Positive

- Changing workspace routing policy immediately affects the next request
- Fallback to environment provider when no eligible accounts exist
- Foundation for future health checks, failover, and borrowing (not implemented)

### Negative

- Extra DB reads per request (accounts, usage aggregates)
- Preview endpoint uses synthetic conversation context

## References

- `app/routing/engine.py`
- `app/routing/policy.py`
- `app/ai/gateway.py`
- Migration `014_routing_engine.py`
