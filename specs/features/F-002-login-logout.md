# F-002 — Login and logout

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `POST /v1/auth/login`, `POST /v1/auth/logout`

## User story

As a registered user, I want to sign in with email and password and sign out so that my session is under my control.

## Acceptance criteria

### Login

1. **Given** valid credentials, **when** I login, **then** response includes `access_token`, `refresh_token`, `token_type`, `expires_in` (seconds for access token).
2. **Given** invalid credentials, **when** I login, **then** API returns `401` with a generic message (same for unknown email and wrong password).
3. **Given** successful login, **when** refresh is issued, **then** refresh token is persisted as a hash with `user_id`, `expires_at`, `created_at`.

### Logout

1. **Given** a valid refresh token, **when** I logout, **then** that refresh row is deleted or marked revoked and cannot be used again.
2. **Given** only access token (no refresh in body), **when** logout, **then** `401` or `422` per OpenAPI (client should send refresh).

## Out of scope (Wave 1)

- “Remember me” as a separate backend feature (optional longer TTL later)
- Listing or revoking other sessions

## References

- [auth-flows.md](../security/auth-flows.md)
- ADR-0003
