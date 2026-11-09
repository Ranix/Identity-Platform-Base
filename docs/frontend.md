# Frontend (SPA)

Official **Single Page Application** for Identity Platform — Wave 1. Implements [specs/ux/screens-mvp.md](../specs/ux/screens-mvp.md) and consumes [specs/api/openapi.yaml](../specs/api/openapi.yaml).

**Run locally:** see [README — Frontend SPA](../README.md#frontend-spa).

---

## Role in the project

The SPA is the only Wave 1 client. It does not host business logic for other apps; it calls the Identity API for registration, session, profile, and password flows.

---

## Stack

| Technology | Purpose in this repo |
|------------|----------------------|
| **Vite** | Dev server, production build, **proxy** to the API in local dev |
| **React 18** | UI components and state |
| **TypeScript** | Types aligned with API responses (`UserPublic`, tokens) |
| **React Router 7** | URL routes without full page reloads |
| **React Hook Form** | Forms (login, register, profile, passwords) |
| **Tailwind CSS 4** | Utility styling; dark theme, mobile-first layout |

All server-state loading is hand-rolled `apiFetch`/`apiFetchAuth` inside effects and submit handlers — no data-fetching library. `@tanstack/react-query` was wired but unused and was removed (docs/tech-debt.md item 15); revisit only if manual loading/error handling actually becomes a pain point.

`package.json` also lists `@hookform/resolvers` and `zod` — not connected yet (Wave 2 [F-009](../specs/features/F-009-spa-form-validation.md) infrastructure landed early; see docs/tech-debt.md item 16).

---

## Folder layout

```text
frontend/
├── index.html              # HTML shell, mobile viewport
├── vite.config.ts          # Port 5173; proxy /v1, /health → :8000
├── package.json
├── tsconfig.json
└── src/
    ├── main.tsx            # React root
    ├── App.tsx             # Router + providers
    ├── index.css           # Tailwind import
    ├── lib/
    │   ├── api.ts          # fetch wrapper + shared types
    │   └── auth.tsx        # Session context (login / logout / refresh)
    ├── routes/
    │   └── ProtectedRoute.tsx
    ├── components/
    │   └── ui.tsx          # Shell, buttons, fields (minimal design system)
    └── pages/              # One screen per route
        ├── LandingPage.tsx
        ├── RegisterPage.tsx
        ├── LoginPage.tsx
        ├── ForgotPasswordPage.tsx
        ├── ResetPasswordPage.tsx
        ├── DashboardPage.tsx
        ├── ProfilePage.tsx
        └── SecurityPage.tsx
```

---

## Application bootstrap

```text
main.tsx
  └── App.tsx
        └── BrowserRouter
              └── AuthProvider    ← tokens + user (wraps routes)
                    └── Routes (public | protected)
```

---

## API layer (`src/lib/api.ts`)

- **`VITE_API_URL`**: empty in dev → requests go to the same origin (`/v1/...` on port 5173).
- **Vite proxy** forwards `/v1` and `/health` to `http://localhost:8000` (avoids CORS in dev).
- **Production:** set `VITE_API_URL` to the API origin; ensure backend CORS allows the SPA origin.
- **`apiFetch`**: JSON headers, optional `Authorization: Bearer`, parses FastAPI `detail` errors, handles `204` with no body.

There is no global 401 interceptor yet; protected pages call `refreshSession()` when the access token is missing.

---

## Session (`src/lib/auth.tsx`)

**Target behavior:** [F-007](../specs/features/F-007-spa-session-client.md) (implemented).

| Data | Storage | Rationale |
|------|---------|-----------|
| Access JWT | React state (memory) | Short-lived; cleared on full reload |
| `accessExpiresAt` | React state (memory) | Drives proactive refresh (F-007) |
| Refresh token | `sessionStorage` (`identity_platform_refresh`) | Survives tab reload in the same browser session |
| User profile | React state | Dashboard and forms |
| `authStatus` | React state (F-007) | `loading` \| `authenticated` \| `anonymous` for ProtectedRoute |

### Flows

**Login:** `POST /v1/auth/login` → store tokens → `GET /v1/users/me` → set `user`.

**Logout:** `POST /v1/auth/logout` with refresh (best effort) → clear state and `sessionStorage`.

**Refresh:** `POST /v1/auth/refresh` → new access, same refresh (Wave 1 backend). On failure → logout.

**Bootstrap on load:** If refresh exists but access does not (e.g. after F5), refresh once and load `/users/me`. Runs once on mount in `AuthProvider`.

**Hook:** `useAuth()` exposes `login`, `logout`, `refreshSession`, `user`, `accessToken`, `setUser`.

See also [specs/security/auth-flows.md](../specs/security/auth-flows.md) and [ADR-0003](../adr/0003-mvp-token-session-model.md).

---

## Routing and protection

| Route | Page | Auth |
|-------|------|------|
| `/` | Landing | Public |
| `/register` | Register | Public |
| `/login` | Login | Public |
| `/forgot-password` | Request reset | Public |
| `/reset-password?token=` | Confirm reset | Public |
| `/dashboard` | Dashboard | Protected |
| `/profile` | Profile | Protected |
| `/security` | Change password | Protected |

**Current (F-007):** `authStatus` drives `ProtectedRoute` (loading spinner, redirect when anonymous).

**F-008:** logout via `useLogout()` redirects to `/`; `ButtonLink` for nav actions.

---

## Screens and API calls

| Page | Endpoints / behavior |
|------|----------------------|
| **Landing** | Links only |
| **Register** | `POST /v1/auth/register` → redirect to login |
| **Login** | `useAuth().login()` → `/dashboard` |
| **Forgot password** | `POST /v1/auth/password-reset/request`; generic success copy; local dev uses API logs ([ADR-0004](../adr/0004-password-reset-delivery.md)) |
| **Reset password** | `POST /v1/auth/password-reset/confirm` with `token` from query string |
| **Dashboard** | Displays `user`; links to profile/security; logout |
| **Profile** | `PATCH /v1/users/me` (refresh access first if needed) |
| **Security** | `POST /v1/users/me/password` |

Forms use **React Hook Form** + shared `Field` / `PrimaryButton` from `components/ui.tsx`.

---

## Mobile-first UI (`components/ui.tsx`)

- **`Shell`:** `max-w-md`, centered, `min-h-dvh`
- **Inputs:** large tap targets (`py-3`, `text-base`)
- **Full-width primary actions**
- Dark slate theme (see `index.html` body classes)

No persistent nav bar in Wave 1 — navigation via links between screens.

---

## Spec ↔ code map

| Spec | Code |
|------|------|
| [specs/ux/screens-mvp.md](../specs/ux/screens-mvp.md) | `App.tsx` routes + `pages/*` |
| [specs/ux/user-journeys-wave1.md](../specs/ux/user-journeys-wave1.md) | Journeys, E2E checklist, bug report template |
| [specs/api/openapi.yaml](../specs/api/openapi.yaml) | `api.ts` types and fetch paths |
| [specs/features/F-00x](../specs/features/) | Expected behavior per feature |
| [F-007](../specs/features/F-007-spa-session-client.md) | Session client (refresh, 401, loading) |
| [F-008](../specs/features/F-008-spa-ui-polish.md) | Logout redirect, ButtonLink |
| [F-009](../specs/features/F-009-spa-form-validation.md) | Zod (Wave 2) |
| [specs/security/auth-flows.md](../specs/security/auth-flows.md) | `auth.tsx` |

When the contract changes: update OpenAPI and feature spec first ([sdd-workflow.md](sdd-workflow.md)), then `api.ts`, `auth.tsx`, and affected pages.

---

## Roadmap vs current code

| Topic | Wave | Spec | Code status |
|-------|------|------|-------------|
| Proactive JWT refresh before expiry | 1 | F-007 | Implemented |
| Protected route loading during bootstrap | 1 | F-007 | Implemented |
| Automatic 401 → refresh → retry | 1 | F-007 | Implemented |
| Logout redirect to `/` | 1 | F-008 | Implemented |
| `ButtonLink` (no nested Link+button) | 1 | F-008 | Implemented |
| Zod + RHF validation | 2 | F-009 | Pending (criteria 1–2); criteria 3–5 (422→field mapping, required messages, client-side mirrors of server rules) implemented in Wave 1 — see `lib/formErrors.ts`, `lib/validators.ts` |
| Vitest + Playwright | 3 | waves.md | Pending |

---

## Related documentation

- [README](../README.md) — project index and quick start
- [docs/vision.md](vision.md) — SPA as official client, mobile-first principles
- [docs/glossary.md](glossary.md) — SPA, access/refresh token definitions
