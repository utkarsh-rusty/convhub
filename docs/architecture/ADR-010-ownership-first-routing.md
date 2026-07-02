# ADR-010: Ownership-First Routing

## Status

Accepted — Sprint 13

## Context

ConvHub originally treated workspace credits as a universal gate: when a user's credit balance hit zero, the gateway attempted to borrow or returned HTTP 402 before considering which AI providers the user personally owned.

That model conflated two concerns:

1. **Provider ownership** — whose API keys and accounts execute the request
2. **Borrowing governance** — how much shared usage teammates may consume

Workspace members can own multiple AI accounts (Groq, Anthropic, OpenAI, Gemini, Ollama, etc.). Routing should prefer the sender's own providers and only involve teammates when the sender has no usable provider.

## Decision

Adopt **ownership-first routing** as the default for all workspaces (`hard_budget_enforcement = false`).

### Routing order

1. Load active AI accounts owned by the **message sender**
2. Filter to healthy providers
3. Apply the workspace routing policy **only on sender accounts**
4. If a provider is selected → execute (no borrowing)
5. If no usable sender provider → **BorrowEngine** selects a lender from **conversation participants** (excluding sender)
6. Route **only among the lender's providers** → execute

Borrowing is triggered by **provider exhaustion**, not by zero ConvHub credits.

### Credits redefined

| Mode | Own providers | Borrowed usage |
|------|---------------|----------------|
| Ownership-first (default) | Never blocked by credit balance; usage may exceed monthly allocation with a warning | Governed by lender `monthly_share_limit` minus `lent_credits` |
| Hard budget (`hard_budget_enforcement = true`) | Legacy behaviour — credits block all paid usage | Same borrow rules when sender has no providers |

### Borrowing scope

- Lenders must be **conversation participants** (never outsiders)
- Lender selection uses existing `LendingPreference` (`auto_share_enabled`, `monthly_share_limit`, `minimum_reserved_credits`)
- Share capacity = `monthly_share_limit - lent_credits` (not lender personal `remaining_credits`)
- HTTP 402 `Borrow limit exceeded` when share capacity is insufficient

### Execution metadata

`ExecutionSummary` reports:

- `execution_type`: `own_provider`, `borrowed_provider`, `local_model`
- `owner_name`, `borrowed_from`, `provider`, `model`, `routing_policy`

## Consequences

### Positive

- Predictable behaviour: users always consume their own providers first
- Credits become a governance layer for sharing, not a blocker for owned API keys
- Conversation-scoped borrowing reduces accidental cross-team usage
- Clear upgrade path via `hard_budget_enforcement` for workspaces that want legacy credit gates

### Negative / trade-offs

- Gateway flow is more complex (sender route → optional borrow → lender route)
- Workspaces with no per-user AI accounts rely entirely on borrowing or free env fallbacks (mock/ollama)
- `OWNER_FIRST` routing policy name still refers to workspace policy semantics, distinct from ownership-first architecture

## Future: Enterprise mode

Enterprise deployments may require:

- Org-wide provider pools with centralized billing
- Stricter hard budgets by default
- Audit trails tying execution to cost centers

Ownership-first routing provides the foundation: provider ownership is explicit before any shared consumption occurs.

## Related

- [ADR-008: Routing Engine](./ADR-008-routing-engine.md)
- [ADR-009: Resource Sharing](./ADR-009-resource-sharing.md)
- [AI Account Ownership](./ai-account-ownership.md)
