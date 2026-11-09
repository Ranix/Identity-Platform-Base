# Security requirements (Wave 1)

## Passwords

- Minimum length: **8** characters (Wave 1); increase in Wave 2 if needed
- Maximum length: **72 bytes** — the bcrypt hashing limit. Reject longer input with `422`, never let it reach bcrypt unguarded (a raw `ValueError` there surfaces as an unhandled `500`; see `docs/tech-debt.md` item 24)
- Stored with **bcrypt**; never plaintext or reversible encryption
- Registration and reset: require confirmation field on client; server validates match

## Tokens

- Access JWT: signed (HS256 or RS256 — see ADR-0003); include `sub` (user id), `exp`, `iat`
- Access TTL: **15 minutes** (configurable via env)
- Refresh: cryptographically random (≥ 32 bytes), stored **hashed** (SHA-256 of token acceptable for opaque tokens)
- Refresh TTL: **7 days** (configurable)
- Password reset token: random, hashed at rest, TTL **1 hour**, single use

## Secrets

- `JWT_SECRET` must not be the repository's placeholder default and must be **at least 32 characters** outside `ENVIRONMENT=local`; the API refuses to start otherwise (see [ADR-0003](../../adr/0003-mvp-token-session-model.md) consequences).

## API

- Generic errors on login failure and password reset request (no account enumeration on reset)
- Registration may return `409` on duplicate email (acceptable trade-off for Wave 1; reset stays generic)
- Rate limiting: defer to Wave 2; note in backlog

## Transport

- Local: HTTP allowed
- Production (Wave 3): TLS required

## Headers

- Authenticated routes: `Authorization: Bearer <access_token>`

## Logging

- Never log passwords, refresh tokens, reset tokens, or JWT secrets
- Dev reset delivery logs token only when `ENVIRONMENT=local` (ADR-0004)
