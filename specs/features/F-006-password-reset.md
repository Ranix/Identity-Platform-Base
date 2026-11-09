# F-006 — Password reset

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `POST /v1/auth/password-reset/request`, `POST /v1/auth/password-reset/confirm`

## User story

As a user who forgot my password, I want to reset it using a time-limited token so that I can access my account again.

## Acceptance criteria

### Request

1. **Given** any email string, **when** I request reset, **then** API returns `202` or `200` with the **same message** whether or not the account exists (anti-enumeration).
2. **Given** a registered email, **when** request succeeds, **then** a single-use token is stored hashed with expiry (e.g. 1 hour) and delivery follows ADR-0004.

### Confirm

1. **Given** valid token and new password meeting policy, **when** I confirm, **then** password updates and token is consumed.
2. **Given** expired or used token, **when** I confirm, **then** `400` with generic error.
3. **Given** a successful confirm, **when** complete, **then** all of the user's refresh tokens are revoked server-side, invalidating any session that existed before the reset — including sessions on other devices (see ADR-0003 addendum).

## Delivery slices

| Slice | Wave | Channel |
|-------|------|---------|
| Token generation + confirm API | 1 | — |
| Local dev delivery | 1 | Server log / structured dev output (ADR-0004) |
| Email link | 2 | SMTP/SES |

## References

- ADR-0004
- [auth-flows.md](../security/auth-flows.md)
