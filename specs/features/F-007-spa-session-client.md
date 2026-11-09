# F-007 — SPA session client

> **Status:** implemented  
> **Wave:** 1 (completion slice — closes 15-minute access TTL gap)  
> **OpenAPI:** uses existing `POST /v1/auth/refresh` (F-003)  
> **Code:** `frontend/src/lib/auth.tsx`, `frontend/src/lib/api.ts`, `frontend/src/routes/ProtectedRoute.tsx`

## User story

As a signed-in user using the SPA, I want my session to stay valid while I use the app and recover cleanly after a tab reload, so that I am not logged out unexpectedly when the access token expires.

## Background

Access JWT TTL is ~15 minutes ([requirements.md](../security/requirements.md), ADR-0003). The backend refresh endpoint exists (F-003). The SPA must orchestrate refresh on the client without new API endpoints.

## Acceptance criteria

### Access expiry tracking

1. **Given** login or refresh returns `expires_in`, **when** tokens are stored, **then** the client computes `accessExpiresAt` (epoch ms) in memory.
2. **Given** a scheduled proactive refresh, **when** current time is within **2 minutes** before `accessExpiresAt`, **then** the client calls `POST /v1/auth/refresh` once and updates access + `accessExpiresAt`.
3. **Given** logout, **when** session clears, **then** any proactive refresh timer is cancelled.

### Bootstrap after reload

1. **Given** `sessionStorage` contains a refresh token and no access token, **when** the app mounts, **then** auth state is `loading` until refresh + `GET /v1/users/me` completes or fails.
2. **Given** bootstrap succeeds, **then** auth state is `authenticated` and protected routes render content.
3. **Given** bootstrap fails, **then** auth state is `anonymous`, refresh is cleared, user is redirected from protected routes to `/login`.

### Protected routes

1. **Given** auth state `loading`, **when** user hits a protected route, **then** show a loading UI (spinner or skeleton), not empty dashboard.
2. **Given** auth state `anonymous`, **when** user hits a protected route, **then** redirect to `/login`.

### Automatic retry on 401

1. **Given** an authenticated API call returns **401**, **when** a refresh token exists, **then** the client attempts **one** refresh (mutex — no parallel refresh storms) and retries the original request with the new access token. This mutex is shared by every refresh trigger — 401 retry, proactive timer, bootstrap, and visibility change — not just this one, since Wave 3 refresh rotation with reuse detection will treat two concurrent refreshes on the same token as theft.
2. **Given** refresh fails on 401 retry, **then** logout client-side and redirect to `/login`.
3. **Given** a public route call (login, register, reset), **when** 401 occurs, **then** no refresh retry.

### Visibility (optional but recommended)

1. **Given** the tab becomes visible again, **when** access expires within 2 minutes, **then** trigger proactive refresh.

## Out of scope

- Refresh token rotation (Wave 3)
- httpOnly cookie refresh (Wave 3 hardening)
- Server-side session list UI

## References

- [auth-flows.md](../security/auth-flows.md) — client session diagrams
- F-002, F-003
- [docs/frontend.md](../../docs/frontend.md)

## Implementation notes

- Expose `authStatus: 'loading' | 'authenticated' | 'anonymous'` from `AuthProvider`.
- Centralize authenticated fetch in `api.ts` (or `authenticatedFetch`) with 401 retry; public calls use plain `apiFetch`.
- A single refresh mutex, exported from `api.ts`, is used by every refresh trigger in `auth.tsx` (401 retry, proactive timer, bootstrap, visibility change) — never call the raw refresh function directly from any of them.
