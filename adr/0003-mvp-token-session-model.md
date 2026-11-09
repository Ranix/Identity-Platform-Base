# ADR-0003: MVP token and session model

## Status

Accepted

## Context

Wave 1 needs access + refresh for the SPA without OAuth2 yet. Logout must invalidate server-side session state.

## Decision

- **Access token:** JWT, HS256, signed with `JWT_SECRET` from environment, TTL default 15 minutes, claims `sub`, `iat`, `exp`.
- **Refresh token:** Opaque random string returned once to client; persist **SHA-256 hash** in `refresh_tokens` with expiry default 7 days.
- **Refresh endpoint:** Returns new access JWT; **does not rotate** refresh in Wave 1.
- **Logout:** Client sends refresh token; server deletes matching row.
- **Validation:** FastAPI dependency validates Bearer JWT on protected routes.

## Consequences

- Stolen refresh token works until expiry or logout — rotation deferred to Wave 3
- `JWT_SECRET` must be strong and rotated with care in production
- Multiple devices = multiple refresh rows (no UI until later)

## Future

- Wave 3: refresh rotation + reuse detection
- Wave 4: OIDC for third-party clients

## Addendum (2026-08-25): revoke all refresh tokens on password change/reset

**Status:** Accepted

**Context:** F-005 originally deferred refresh-token revocation on password
change to Wave 3, contingent on updating this ADR. Code review found that
leaving refresh tokens valid after a password change lets a stolen refresh
token survive the exact action meant to lock it out (`docs/tech-debt.md`,
item 1).

**Decision:** Pull this forward into Wave 1. `POST /v1/users/me/password`
and `POST /v1/auth/password-reset/confirm` now delete every `refresh_tokens`
row for the user in the same transaction as the password-hash update.

**Consequences:**
- Changing your password logs out every session, including the one used to
  make the change — the SPA must treat a successful change as an implicit
  logout.
- Password reset already implies the user is signed out on that device;
  this additionally invalidates any *other* active session for the account
  (e.g. an attacker's).
- No change to the refresh token's opaque/hashed design — this only adds a
  bulk delete by `user_id`.
