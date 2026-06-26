# ADR-009: Resource Sharing Engine

## Status

Accepted — 2026-06-26

## Context

Sprint 9B added per-user credit budgets and enforcement. Members who exhaust their
monthly allocation cannot send paid AI requests unless the workspace allows borrowing
from teammates who opt in to sharing.

Requirements:

- Automatic borrowing when a member has zero remaining credits
- Policy-driven lender selection (share limits, minimum reserve, priority)
- Full audit trail: who lent, who borrowed, how much, which strategy
- Must not couple borrowing to provider routing or account selection

## Decision

Introduce a **Resource Sharing Engine** (`BorrowEngine`) as a separate subsystem
between budget pre-check and routing:

```
Gateway → Budget check → BorrowEngine → RoutingEngine → Provider
```

### Separation of concerns

| Subsystem | Responsibility |
|-----------|----------------|
| **Budget / Ledger** | Allocations, usage, immutable `CreditTransaction` entries |
| **BorrowEngine** | Find lenders, validate policy, transfer credits between members |
| **RoutingEngine** | Select `AIAccount` and model — unchanged by borrowing |
| **Provider** | Execute inference — unchanged |

Borrowing answers *"does this user have spendable credits?"* Routing answers
*"which provider account should execute the request?"* These are orthogonal.

### Data model

- **`LendingPreference`** — per-member opt-in: auto-share, monthly limit, minimum
  reserve, lender priority
- **`BorrowRecord`** — audit log linking `AIRequest` → borrower → lender → credits
  → strategy. Separate from `CreditTransaction` (accounting vs. sharing policy)

### Ledger entries

On reserve:

- `CreditTransaction` type `LEND` (from lender)
- `CreditTransaction` type `BORROW` (to borrower)

On successful request completion:

- `BorrowRecord` persisted

On failure after reserve:

- Budget reversal via `ADJUSTMENT` (immutable ledger; no deletion)

### Strategy pattern

`BorrowStrategy` is an abstract interface. `HighestRemainingStrategy` is the
initial implementation. The registry supports additional strategies without
changing gateway or routing code.

## Consequences

**Positive**

- Exhausted members can continue working when teammates share credits
- Owners/admins can audit sharing via workspace overview API
- Routing and providers remain isolated and testable

**Negative**

- Gateway performs a preliminary cost estimate before routing (conservative;
  reconciled after routing selects provider/model)
- Failed requests after reserve require explicit release logic

## Alternatives considered

1. **Routing-aware borrowing** — reject; couples credit policy to account selection
2. **Single pooled workspace budget** — reject; loses per-member accountability
3. **Borrow inside BudgetService** — reject; mixing accounting with sharing policy
