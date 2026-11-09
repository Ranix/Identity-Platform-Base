# F-004 — Profile

> **Status:** approved  
> **Wave:** 1  
> **OpenAPI:** `GET /v1/users/me`, `PATCH /v1/users/me`

## User story

As an authenticated user, I want to view and update my profile so that my identity information stays correct.

## Acceptance criteria

1. **Given** a valid access token, **when** I GET `/v1/users/me`, **then** I receive id, email, first_name, last_name, phone (nullable), locale, timezone, created_at (no password fields).
2. **Given** valid PATCH fields, **when** I update profile, **then** changes persist and response reflects updated user.
3. **Given** email change to an address already used, **when** PATCH, **then** `409`.
4. **Given** no or invalid token, **when** I access `/v1/users/me`, **then** `401`.
5. **Given** a PATCH that changes `email` to a different address, **when** it succeeds, **then** `email_verified` resets to `false` for the new address — Wave 2 verification must confirm it again before it can be trusted.
6. **Given** a PATCH with an out-of-range `phone`/`locale`/`timezone`, or a `timezone` that is not a valid IANA name, **when** I submit it, **then** `422` (never a raw database error).
7. **Given** a PATCH sending explicit JSON `null` for a required field (`first_name`, `last_name`, `email`), **when** I submit it, **then** `422` naming that field — never a `409` or a raw database constraint error. **Given** a PATCH sending an empty string for the nullable `phone` field, **when** I submit it, **then** it clears `phone` to `null` and returns `200` (an empty string is not the same as an out-of-range value under criterion 6).

## Wave 1 fields

| Field | Required on register | Editable |
|-------|---------------------|----------|
| first_name | Yes | Yes |
| last_name | Yes | Yes |
| email | Yes | Yes |
| phone | No | Yes |
| locale | Default `es` or `en` | Yes |
| timezone | Default UTC | Yes |

## Out of scope

- Profile photo (future)

## References

- [model.md](../data/model.md)
