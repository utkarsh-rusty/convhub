# ADR-007: Credit Policy and Budget Enforcement

## Status

Accepted — 2026-06-26

## Context

Sprint 9A introduced the credit ledger (`CreditTransaction`) and budget cache
(`UserBudget`). Every completed AI request records usage, but nothing prevented
requests when credits were exhausted, and pricing was hard-coded in
`credit_calculator.py`.

Sprint 9B must enforce budgets before providers are invoked and separate
**pricing policy** from **accounting**.

## Decision

### CreditPolicy owns pricing

`CreditPolicy.calculate_cost(provider, model, input_tokens, output_tokens)`:

- Base formula: `(input + output) / 1000`
- Provider multipliers: Ollama/Mock = `0.00`, Anthropic/OpenAI/Gemini = `1.0`
- Returns `Decimal`, rounded UP to 2 decimal places
- TODO hooks for per-model rates and workspace pricing plans

`CreditPolicy.estimate_request_cost()` produces a conservative pre-flight cost
from `PromptContext` (character-based input estimate + max output buffer) used
only for budget checks.

### BudgetService owns accounting

| Method | Role |
|--------|------|
| `has_available_credits()` | Pre-flight check after `reset_if_needed()` |
| `consume_credits()` | Post-completion charge; raises `InsufficientCreditsError` |
| `adjust_credits()` | Reconcile estimate vs actual delta |
| `reset_if_needed()` | Automatic monthly reset with ALLOCATION ledger row |

`CreditTransaction` remains the immutable source of truth. `UserBudget` is the
read-optimized cache.

### Gateway enforcement flow

```
1. reset_if_needed(user)
2. estimated = CreditPolicy.estimate_request_cost(...)
3. if estimated > 0 and not has_available_credits(estimated) → HTTP 402
4. provider.generate(...)        ← never reached when blocked
5. actual = CreditPolicy.calculate_cost(completed AIRequest)
6. consume_credits(actual)
7. if actual ≠ estimated → adjust_credits(estimated - actual)
```

Free providers (Ollama, Mock) produce `estimated = 0`, so zero-credit users can
still use local/free models. Paid providers require sufficient credits.

### WorkspaceBudgetSettings

Per-workspace policy flags (borrowing, emergency pool, local models) and
default monthly allocation. Admin API at
`GET/PATCH /workspaces/{id}/settings/budget` (Owner/Admin).

## Why pricing is separate from accounting

- **CreditPolicy** answers "how much should this cost?" — changes with provider
  rates, model tiers, and future pricing plans.
- **BudgetService** answers "what happened to the balance?" — append-only ledger,
  never embeds pricing formulas.
- Pricing can evolve without touching ledger schema or provider adapters.

## Why enforcement happens before providers

- Prevents spending external API tokens when the user cannot pay
- Protects workspace budgets from overdraft (borrowing not yet implemented)
- Fail-fast with HTTP 402 gives clear UX without partial AIRequest side effects

## Why actual cost may differ from estimated cost

Pre-flight estimation uses character heuristics and a max output buffer because
token counts are unknown until the provider responds. After completion:

- **Actual** tokens drive the USAGE charge
- **Delta** between estimate and actual is reconciled via ADJUSTMENT for audit
- Conservative estimates minimize post-completion insufficient-credit failures

## Consequences

### Positive

- Clear separation: Policy (pricing) vs Service (accounting) vs Gateway (orchestration)
- Zero-credit users blocked from paid providers, not from free local models
- Workspace settings ready for future routing without implementing it now

### Negative

- Character-based estimation is imprecise; may over- or under-estimate vs real tokens
- Reconciliation ADJUSTMENT adds ledger rows when estimate ≠ actual

## References

- `app/resource_management/credit_policy.py`
- `app/resource_management/budget_service.py`
- `app/ai/gateway.py`
- Migration `013_workspace_budget_settings.py`
