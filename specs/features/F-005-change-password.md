# F-005 — Change password

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `POST /v1/users/me/password`

## User story

As an authenticated user, I want to change my password by confirming my current password so that my account stays secure.

## Acceptance criteria

1. **Given** valid access token and correct `current_password`, **when** I submit `new_password` + confirmation, **then** password hash updates and I receive `204` or success payload per OpenAPI.
2. **Given** wrong `current_password`, **when** I submit, **then** `401` or `400` with generic error (no leak).
3. **Given** new password fails policy, **when** I submit, **then** `422` with validation details.
4. **Given** successful change, **when** complete, **then** all of the user's refresh tokens — including the one backing the current session — are revoked server-side in the same transaction as the password update (see ADR-0003 addendum). The SPA treats a successful change as an implicit logout and redirects to `/login`.

## References

- [requirements.md](../security/requirements.md)
