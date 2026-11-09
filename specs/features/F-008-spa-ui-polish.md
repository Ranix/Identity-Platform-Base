# F-008 — SPA UI polish (Wave 1)

> **Status:** implemented  
> **Wave:** 1 (polish slice)  
> **Code:** `frontend/src/pages/*`, `frontend/src/components/ui.tsx`

## User story

As a user, I want clear navigation and feedback after sign-out and consistent button links, so that the SPA feels intentional and mobile-friendly.

## Acceptance criteria

### Logout navigation

1. **Given** I sign out from dashboard or security, **when** logout completes, **then** I am redirected to `/` (replace history).
2. **Given** I sign out, **when** session is cleared, **then** I cannot access protected routes without logging in again.

### Button links

1. **Given** dashboard (and similar) navigation actions, **when** rendered, **then** use a single focusable control (`ButtonLink` or equivalent) — no nested `<Link><button></Link>`.

### UX alignment

1. Loading and error patterns follow [screens-mvp.md](../ux/screens-mvp.md) (F-007 covers loading on protected routes).

## Out of scope

- Zod validation (Wave 2 — F-009)
- E2E tests (Wave 3)

## References

- [screens-mvp.md](../ux/screens-mvp.md)
- [docs/frontend.md](../../docs/frontend.md)
