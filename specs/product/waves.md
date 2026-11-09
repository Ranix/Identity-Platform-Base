# Delivery waves

## Wave 1 – Local core

**Environment:** local (Docker Compose).  
**Primary consumer:** responsive SPA (mobile-first UI).

### Includes

- Registration (email stored; no email verification)
- Login, logout (refresh revoked server-side)
- Access JWT + refresh token (DB-backed, no rotation)
- Token refresh
- Profile read/update
- Change password (authenticated)
- Password reset (full flow; **local delivery** of reset token per ADR-0004)
- Landing, auth screens, dashboard, profile, security UI
- OpenAPI documented, basic tests, Docker Compose

### Wave 1 completion slices (SPA)

Backend and screens may land before these; they **close Wave 1** for real daily use:

| Slice | Spec | Summary |
|-------|------|---------|
| Session client | [F-007](../features/F-007-spa-session-client.md) | Proactive refresh, 401 retry, bootstrap loading, `authStatus` |
| UI polish | [F-008](../features/F-008-spa-ui-polish.md) | Logout → `/`, `ButtonLink` pattern |

### Excludes

- Email verification
- Real transactional email (SMTP/SES)
- Refresh rotation, active sessions UI, revoke other devices
- OAuth2/OIDC, RBAC
- Native mobile apps
- Zod form validation (Wave 2 — F-009)
- Frontend automated tests (Wave 3)

### Definition of Done

- [ ] All Wave 1 feature specs **F-001 … F-006** implemented (backend + screens)
- [ ] **F-007** and **F-008** implemented (SPA session + polish)
- [ ] `specs/api/openapi.yaml` matches running API
- [ ] SPA covers screens in `specs/ux/screens-mvp.md`
- [ ] `docker compose up` runs API + PostgreSQL (+ frontend when added)
- [ ] Pytest suite passes for auth, profile, password flows
- [ ] README documents env vars and local reset-token behavior
- [ ] Manual E2E: stay logged in >15 min on dashboard OR verify proactive refresh / 401 retry

---

## Wave 2 – Identity hardening

- Email verification
- Real email for reset (and verify)
- Stronger password policy and rate limiting
- SPA: [F-009](../features/F-009-spa-form-validation.md) (Zod + RHF)

## Wave 3 – Pre-prod / production

- HTTPS, secrets management, observability
- Refresh token rotation (+ reuse detection)
- Operational runbooks
- Frontend: Vitest (unit/integration) + Playwright (E2E) for critical auth flows

## Wave 4 – Ecosystem

- OAuth2/OpenID Connect for third-party apps
- Roles and permissions
