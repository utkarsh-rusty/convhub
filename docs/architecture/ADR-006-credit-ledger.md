# ADR-006: Credit Ledger and User Budget Cache

## Status

Accepted — 2026-06-26

## Context

ConvHub needs auditable accounting for AI usage before implementing routing, borrowing,
budget enforcement, or workspace-level policies. Every AI request consumes credits that
must be traceable, reconcilable, and attributable to a workspace member.

Requirements:

- Full audit trail for every credit movement
- Per-member budget visibility inside a workspace
- Automatic deduction after successful AI requests
- Foundation for future borrowing, routing, and policy engines

## Decision

Implement a **double-entry-style ledger** with two tables:

### CreditTransaction (source of truth)

Append-only, immutable ledger rows. Each row records:

- `transaction_type` — `ALLOCATION`, `USAGE`, `BORROW`, `LEND`, `ADJUSTMENT`
- `amount` — always positive; direction implied by type and from/to users
- `request_id` — links USAGE rows to `AIRequest` records
- `workspace_id`, `from_user_id`, `to_user_id`

**CreditTransaction is never updated or deleted.** Corrections use new `ADJUSTMENT`
rows.

### UserBudget (materialized cache)

One row per `(workspace_id, user_id)` holding:

- `monthly_credit_limit`, `used_credits`, `borrowed_credits`, `lent_credits`
- `remaining_credits` — fast read path for UI and future enforcement
- `reset_date` — next monthly allocation boundary

**UserBudget is a cache derived from the ledger.** It exists for query performance and
UI convenience. If cache and ledger diverge, the ledger wins during reconciliation.

### BudgetService

Centralizes all credit mutations:

| Method | Ledger | Cache |
|--------|--------|-------|
| `create_budget()` | ALLOCATION | Initialize limits |
| `allocate_monthly_credits()` | ALLOCATION | Reset monthly counters |
| `record_usage()` | USAGE | `used_credits +=`, `remaining_credits -=` |
| `adjust_credits()` | ADJUSTMENT | Apply delta |

### Gateway integration

After a successful `AIRequest`:

1. `calculate_credits(ai_request)` — `(input_tokens + output_tokens) / 1000`, round UP
2. `BudgetService.record_usage()` — ledger + cache update

No blocking or budget checks yet — accounting only.

## Why the ledger is immutable

- **Auditability** — regulators and workspace admins can reconstruct any balance from history
- **Debugging** — disputes trace back to a specific AI request
- **Future borrowing** — BORROW/LEND rows compose without rewriting prior state
- **Reconciliation** — cache can be rebuilt from transactions if corrupted

## Architecture

```
AI Request (completed)
        ↓
 credit_calculator.calculate_credits()
        ↓
 BudgetService.record_usage()
        ↓
 CreditTransaction (USAGE)  +  UserBudget update
```

Future routing and borrowing plug into `BudgetService` without changing the gateway's
accounting hook.

## Consequences

### Positive

- Every AI call produces a reconcilable audit trail
- Budget API can serve the frontend without scanning the full ledger
- BORROW/LEND enum values reserved for Phase 2 without schema changes

### Negative

- Cache/ledger consistency must be maintained in every service method
- Monthly reset requires a scheduled job calling `allocate_monthly_credits()` (not yet built)

## References

- `app/models/credit_transaction.py`
- `app/models/user_budget.py`
- `app/resource_management/budget_service.py`
- `app/resource_management/credit_calculator.py`
- Migration `012_credit_ledger.py`
