# MVP scope matrix

Long-term product MVP vs **Wave 1** (first iteration). Use tags in backlog: `wave-1`, `wave-1-spa-session`, `wave-1-spa-polish`, `wave-2`, `wave-3`, …

| Capability | Product MVP | Wave 1 | Notes |
|------------|-------------|--------|-------|
| User registration | Yes | Yes | Email unique; no verify |
| Login | Yes | Yes | Email + password |
| Logout | Yes | Yes | Revokes refresh in DB |
| Access JWT | Yes | Yes | Short TTL |
| Refresh token | Yes | Yes | Hashed in DB; no rotation |
| Session refresh | Yes | Yes | API F-003 |
| SPA proactive refresh + 401 retry | Yes | Yes | F-007 (Wave 1 completion) |
| SPA protected-route loading | Yes | Yes | F-007 |
| SPA logout → home | Yes | Yes | F-008 |
| Profile view/edit | Yes | Yes | Name, last name, email, phone, locale, timezone |
| Change password | Yes | Yes | Requires current password |
| Password reset | Yes | Yes | Token delivery: local dev channel (ADR-0004) |
| SPA Zod form validation | No | No | Wave 2 — F-009 |
| SPA automated tests | No | No | Wave 3 — Vitest + Playwright |
| Email verification | Yes | No | Wave 2 |
| Password reset email | Yes | Simulated | Wave 2 real delivery |
| Remember me | Optional UX | Defer | Longer refresh TTL can be added later |
| Profile photo | No | No | Future |
| Active sessions UI | No | No | Wave 3+ |
| Refresh rotation | No | No | Wave 3 |
| OAuth2/OIDC | Future | No | Wave 4 |
| Roles/permissions | Future | No | Wave 4 |

## Consumer matrix

| Consumer | Wave 1 | Future |
|----------|--------|--------|
| Official React SPA | Yes | Yes |
| Native mobile | No | Yes (via OIDC) |
| Third-party apps | No | Yes (via OIDC) |
