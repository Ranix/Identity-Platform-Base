# F-009 — SPA form validation (Zod)

> **Status:** approved  
> **Wave:** 2  
> **Code:** `frontend/src/pages/*`, shared schemas under `frontend/src/lib/schemas/` (when implemented)

## User story

As a user, I want consistent client-side validation that matches server rules, so that I see clear errors before submitting forms.

## Acceptance criteria

1. **Given** register, login, profile, change password, and reset password forms, **when** validated, **then** use Zod schemas with `@hookform/resolvers/zod`.
2. **Given** Wave 2 API password policy changes, **when** policy updates, **then** Zod schemas and messages are updated in the same delivery slice.
3. **Given** server returns `422`, **when** field errors exist, **then** map to form fields where practical. — **Implemented in Wave 1**, ahead of the Zod migration: `frontend/src/lib/api.ts`'s `HttpError.fieldErrors` plus `frontend/src/lib/formErrors.ts::applyFieldErrors()` map FastAPI's `{loc, msg}` array onto `setError(field, ...)` (`docs/tech-debt.md` item 28). Every form already calls it in its submit `catch` block; the Zod migration (criterion 1) doesn't change this mapping, only what runs before the request is sent.
4. **Given** any form field, **when** it's required, **then** its `register(field, { required: ... })` call uses a message string, never the bare boolean `true` — a boolean still blocks submission but leaves `field.message` as `""`, which every page's `Field` component renders as no visible error at all (`docs/tech-debt.md` item 35).
5. **Given** a field whose value a server-side validator checks against a rule the client can cheaply replicate (a hard technical limit like bcrypt's 72-byte cap, or a shape check like "non-blank after trimming"), **when** the form is built, **then** mirror that rule client-side via a shared helper in `frontend/src/lib/validators.ts` rather than only finding out via the server's `422` — **Implemented in Wave 1** for the bcrypt byte limit (item 24) and the blank-name check (item 32), across every password-setting and name field (`docs/tech-debt.md` item 35). Not required for rules a real user can never violate through normal use (e.g. `LoginPage`'s password can't exceed 72 bytes — it was already capped when set).

## Out of scope

- Wave 1 — the Zod/`@hookform/resolvers` migration itself (criteria 1–2) remains Wave 2; criteria 3–5 describe interim Wave 1 behavior using plain React Hook Form rules, already implemented

## References

- [requirements.md](../security/requirements.md)
- F-001, F-004, F-005, F-006
