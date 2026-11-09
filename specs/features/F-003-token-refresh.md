# F-003 — Token refresh

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `POST /v1/auth/refresh`

## User story

As a signed-in user, I want to obtain a new access token using my refresh token so that I stay authenticated without re-entering my password.

## Acceptance criteria

1. **Given** a valid, non-expired, non-revoked refresh token, **when** I call refresh, **then** I receive a new access JWT and the **same** refresh token (no rotation in Wave 1).
2. **Given** an expired or unknown refresh token, **when** I refresh, **then** API returns `401`.
3. **Given** a valid access token, **when** I call protected endpoints, **then** server validates signature, expiry, and subject.

## Out of scope (Wave 1)

- Refresh token rotation and reuse detection (Wave 3)

## References

- ADR-0003
- [auth-flows.md](../security/auth-flows.md)
