# ADR-005: PromptBuilder and Dumb Providers

## Status

Accepted — 2026-06-26

## Context

ConvHub routes every AI request through a shared gateway that must support multiple LLM
providers (Mock, Anthropic, Ollama, and future OpenAI/Gemini adapters) while preserving
collaboration semantics: multiple humans in one conversation, workspace boundaries, and
per-workspace credentials.

Early implementations mixed concerns:

- Providers received raw messages and sometimes read configuration (model names, base URLs).
- The gateway performed light message mapping inline.
- Workspace and participant context was invisible to the model.

This made it hard to add RAG, conversation snapshots, pinned instructions, or coding
standards without touching every provider.

## Decision

Introduce a **PromptBuilder** as the single component that converts collaboration domain
objects into a **PromptContext** — a provider-agnostic package containing:

- `system_prompt` — workspace/conversation metadata plus configured `AI_SYSTEM_PROMPT`
- `chat_messages` — normalized `system` / `user` / `assistant` messages (user lines
  prefixed with `[Display Name]`)
- `metadata` — structured context for logging, future sections, and gateway bookkeeping

The **Gateway** owns orchestration:

1. Resolve workspace AI account (if any)
2. Choose provider name and model (`AIAccount.default_model` → environment fallback)
3. Load workspace, participants, and author display names
4. Call `PromptBuilder.build(...)`
5. Obtain a provider from the **Provider Factory** (construction only)
6. Invoke `provider.generate(prompt_context, model)`
7. Persist `AIRequest` and assistant `Message`

**Providers are intentionally dumb.** They:

- Accept `PromptContext` and an explicit `model` string
- Translate `PromptContext` into vendor-specific API calls
- Return `AIResponse`

They must **not** query the database, read workspace settings for model selection, or
understand conversation participants.

The **Provider Factory** only constructs provider instances from credentials and
environment endpoints. It never chooses models, builds prompts, or loads workspace data.

## Architecture

```
Conversation + Messages
        ↓
   PromptBuilder
        ↓
   PromptContext
        ↓
      Gateway  ← AIAccount, model selection
        ↓
  Provider Factory
        ↓
     Provider
        ↓
        LLM
```

Every provider receives the **same** `PromptContext` shape. Vendor-specific formatting
(e.g. Anthropic `system` parameter vs Ollama `system` message) stays inside the adapter.

## Future extensibility

`PromptBuilder` reserves metadata keys and TODO hooks for:

| Future capability        | Integration point                          |
|-------------------------|--------------------------------------------|
| Conversation snapshot   | Additional system-prompt section           |
| Retrieved documents     | RAG context block before chat messages     |
| Code context            | Repository/file excerpt section            |
| Workspace memory        | Long-term memory preamble                  |
| Pinned instructions     | Per-conversation override section          |
| Coding standards        | Workspace policy section                   |

Each capability appends provider-agnostic text inside `PromptBuilder` without modifying
provider interfaces.

## Consequences

### Positive

- One place to evolve prompt strategy as collaboration features grow.
- Providers remain thin, testable HTTP/SDK adapters.
- Gateway centralizes model policy (`default_model` per AI account).
- RAG and snapshots can ship incrementally behind PromptBuilder.

### Negative

- Gateway performs additional reads (workspace, participants, authors) per AI request.
  Acceptable for current scale; can be cached later if needed.
- Slightly more indirection when debugging a single provider issue (check PromptContext
  first, then provider).

## Alternatives considered

**Providers build prompts from ORM models** — rejected; couples adapters to ConvHub schema.

**ChatService builds prompts** — rejected; violates “gateway owns orchestration” and would
change a stable service API.

**Per-provider prompt builders** — rejected; duplicates metadata logic and blocks consistent
multi-user formatting.

## References

- `app/ai/prompt_builder.py`
- `app/ai/gateway.py`
- `app/ai/providers/base.py`
- Migration `011_ai_account_default_model.py`
