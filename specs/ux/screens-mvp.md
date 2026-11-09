# Screens (Wave 1 SPA)

Mobile-first layout: single column, touch-friendly controls, bottom-safe padding.

| Route | Screen | Auth |
|-------|--------|------|
| `/` | Landing — project intro, Login, Register | Public |
| `/register` | Registration form (F-001) | Public |
| `/login` | Login + link to forgot password | Public |
| `/forgot-password` | Request reset email (F-006 request) | Public |
| `/reset-password` | New password + token query param | Public |
| `/dashboard` | Welcome + summary of user | Protected |
| `/profile` | Edit profile (F-004) | Protected |
| `/security` | Change password, logout (F-005, F-002) | Protected |

## UX notes

- After login, redirect to `/dashboard`
- After logout, redirect to `/` ([F-008](../features/F-008-spa-ui-polish.md))
- While session bootstrap runs (F-007), protected routes show **loading**, not blank content
- Forgot password: show generic success message always
- Local dev: document that reset link/token appears in API logs
- Errors: inline field errors for `422`; toast or banner for `401`/`409`
- Navigation actions on dashboard use **ButtonLink** (single focusable control)

## Session behavior

See [F-007](../features/F-007-spa-session-client.md) and [auth-flows.md](../security/auth-flows.md).

## User journeys and bugs

End-to-end paths and how to report issues (numbered steps + journey/step ID): [user-journeys-wave1.md](user-journeys-wave1.md).

## Out of scope

- Session list / revoke devices
- Email verification banner (Wave 2)
