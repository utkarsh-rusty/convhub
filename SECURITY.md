# Security Policy

ConvHub is an open-source project for **AI-native project memory**. Security reports help protect workspaces, credentials, and collaboration data.

## Supported versions

Security fixes are applied to the `main` branch.

## Reporting a vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Email the maintainers with:

- Description of the issue
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

We aim to acknowledge reports within 72 hours.

## Sensitive configuration

- Rotate `JWT_SECRET_KEY` and `CREDENTIALS_ENCRYPTION_KEY` in production.
- Never commit `backend/.env` or API keys.
- Use workspace-scoped AI account credentials instead of shared env keys when possible.
