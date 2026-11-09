# F-001 — User registration

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `POST /v1/auth/register`

## User story

As a visitor, I want to create an account with my email and password so that I can sign in to Identity Platform.

## Acceptance criteria

1. **Given** a valid payload (first name, last name, email, password, password confirmation), **when** I register, **then** a user is created with normalized email (lowercase trim), password stored as a secure hash (bcrypt/argon2), and `email_verified = false` (login still allowed in Wave 1).
2. **Given** an email already registered, **when** I register, **then** API returns `409` with a generic conflict message (no user enumeration beyond this case).
3. **Given** password and confirmation differ, **when** I submit (client or server validation), **then** request fails with `422`.
4. **Given** successful registration, **when** response returns, **then** client may proceed to login (auto-login is optional; not required Wave 1).

## Out of scope (Wave 1)

- Sending verification email
- Blocking login until email verified

## References

- [model.md](../data/model.md) — `users`
- [requirements.md](../security/requirements.md) — password rules
