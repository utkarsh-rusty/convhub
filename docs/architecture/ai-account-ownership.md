# AI Account Ownership & Conversation-Aware Routing

Sprint 13 refactors AI accounts from workspace-owned to **user-owned**, while keeping workspace scoping for visibility and policy.

## Ownership Model

- Each `AIAccount` has `owner_user_id` (FK → `users.id`) and `workspace_id`.
- Users create and manage their own accounts; workspace admins can manage any account.
- Migration `017_ai_account_owner` backfills existing accounts to the workspace owner.

## Conversation-Aware Routing

Eligible accounts for a chat request must satisfy:

1. **Owner is an active conversation participant**
2. Account is active
3. Credentials are healthy
4. Provider allowed by workspace settings (e.g. `allow_local_models` for Ollama)

Non-participants' accounts are never considered, even in the same workspace.

## Sender-First Resolution

`SenderFirstAccountResolver` runs before workspace routing policy:

1. Filter healthy accounts to the message sender (`owner_user_id == requesting_user.id`)
2. Pick by **owner priority** (lower `priority` field = preferred)
3. If no sender account is eligible, fall through to participant pool

## Workspace Routing Policy

When sender accounts are unavailable, `AccountRoutingOrchestrator` applies the workspace `routing_policy` to **other participants' accounts** only.

## Borrow Scope

Credit borrowing (`BorrowEngine`) is limited to **conversation participants** who have `auto_share_enabled`, sufficient credits, and reserve headroom. Non-participant workspace members are excluded via `eligible_user_ids`.

## Execution Metadata

`ExecutionSummary` exposes:

| Field | Meaning |
|-------|---------|
| `account_owner_name` | Display name of the AI account owner (user) |
| `execution_type` | `own_account`, `participant_account`, `borrowed`, `local_model` |
| `credits_borrowed_from` | Lender name when credits were borrowed for the request |

## Migration Notes

1. Run `alembic upgrade head` to apply `017_ai_account_owner`.
2. Existing accounts are assigned to each workspace's owner.
3. Members should register their own provider keys; admins retain oversight.

## Flow

```
Workspace
  → Conversation
  → Participants
  → Sender
  → Sender's Accounts (priority)
  → Borrow (participants only)
  → Routing policy on participant accounts
  → Provider
```
