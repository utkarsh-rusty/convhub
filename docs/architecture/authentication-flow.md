# Authentication Flow

```mermaid
sequenceDiagram
    participant Browser
    participant API
    participant AuthService
    participant DB

    Browser->>API: POST /auth/login {email, password}
    API->>AuthService: login()
    AuthService->>DB: verify user + password hash
    AuthService->>DB: store refresh token hash
    AuthService-->>API: access + refresh JWT
    API-->>Browser: TokenResponse

    Browser->>API: Authorized requests (Bearer access token)
    API->>API: decode_access_token → user_id
    API->>DB: load user / workspace membership

    Browser->>API: POST /auth/refresh {refresh_token}
    AuthService->>DB: rotate refresh token
    AuthService-->>Browser: new access + refresh tokens
```

## Demo mode (optional)

When `DEMO_MODE=true`:

- `GET /demo/users` lists Alice, Bob, Charlie personas.
- `POST /demo/login {persona}` issues tokens via the standard `AuthService.login` path using seeded credentials.
- Demo endpoints return **404** when demo mode is disabled.

No changes to production auth when demo mode is off.
