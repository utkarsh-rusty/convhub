# Realtime Events

```mermaid
flowchart LR
    subgraph producers
        Messages[ConversationService]
        Gateway[AIGateway]
        WSManager[WebSocketManager]
    end
    subgraph transport
        Hub[WebSocketManager channels]
    end
    subgraph consumers
        Browser[React SocketProvider]
    end
    Messages --> Hub
    Gateway --> Hub
    WSManager --> Hub
    Hub --> Browser
```

## Event envelope

Every event includes:

- `type` — e.g. `message.created`, `typing.started`, `credits.updated`
- `timestamp`
- `workspace_id`
- `conversation_id` (nullable)
- `payload`

## Channels

- **Workspace** — presence, credits, routing, conversation list invalidation
- **Conversation** — messages, typing, streaming tokens
- **User** — direct notifications (when used)

See `app/realtime/events.py` for the full enum.
