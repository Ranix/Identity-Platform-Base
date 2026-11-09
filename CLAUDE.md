# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working method: Spec-Driven Development

This repo is spec-first. Before writing code, read `docs/sdd-workflow.md`. The rules that matter in practice:

1. **`specs/api/openapi.yaml` is the source of truth for the HTTP contract.** If code and OpenAPI disagree, fix the code or update OpenAPI explicitly — never let them drift silently.
2. **Every capability has a feature spec** in `specs/features/` (F-001 … F-009) that must be `approved` before implementation.
3. **ADRs** (`adr/`) capture hard-to-reverse decisions. ADR-0003 (token/session model) and ADR-0004 (local reset delivery) constrain most auth code.
4. **Delivery is by waves** (`specs/product/waves.md`). Wave 1 = local core. Things absent from the code are often *deliberately deferred*, not forgotten — check the wave scope before "fixing" them.

Known gaps and improvement backlog: `docs/tech-debt.md`.

## Commands

### Backend (`backend/`, Python 3.12 + uv)

```bash
cd backend
uv sync --extra dev                              # install deps
uv run alembic upgrade head                      # apply migrations (needs Postgres up)
uv run uvicorn app.main:app --reload --port 8000 # dev server
uv run pytest                                    # full test suite
uv run pytest tests/test_auth.py::test_logout_revokes_refresh  # single test
uv run ruff check .                              # lint (configured, no npm-style script)
uv run ruff format .                             # format
```

Tests need no database: `tests/test_auth.py` overrides `get_db` with in-memory SQLite.

### Frontend (`frontend/`, React 18 + Vite 6 + TS)

```bash
cd frontend
npm install
npm run dev           # Vite on :5173, proxies /v1 and /health to :8000
npm run build         # tsc -b && vite build
npm run lint          # eslint . (flat config, eslint.config.js)
npm run format        # prettier --write .
npm run format:check  # prettier --check .
```

ESLint (flat config) + Prettier are configured; `eslint-plugin-react-hooks` is pinned to its classic rule set (`rules-of-hooks`, `exhaustive-deps`) rather than the v7 "recommended" config, since that config bundles React Compiler-oriented rules that don't apply to this React 18 codebase. No test runner is configured (frontend tests are Wave 3).

### Full stack

```bash
docker compose up --build     # Postgres + API (:8000) + web (:5173)
./scripts/mobile-public-url.sh  # cloudflared tunnel for phone testing (needs Docker running)
```

`backend/scripts/start.sh` runs `alembic upgrade head` on every container start.

## Architecture

### Two-tier token model (ADR-0003)

- **Access token**: stateless JWT (HS256), 15 min TTL, claims `sub`/`iat`/`exp`. Validated in `app/deps.py::get_current_user`, which decodes then loads the `User` from the DB.
- **Refresh token**: opaque `secrets.token_urlsafe(32)`, returned once, stored as **SHA-256 hash** in `refresh_tokens`. The raw value never touches the DB.
- **Refresh does not rotate** in Wave 1 — `/v1/auth/refresh` returns a *new access token and the same refresh token*.
- **Logout deletes the refresh row.** Nothing can revoke an access token before it expires; a logged-out user keeps API access for up to 15 minutes.

Consequence worth remembering: server-side session state lives *only* in `refresh_tokens`. Any feature that needs to kill a session must delete rows there.

### Backend layering (`backend/app/`)

`main.py` (app + CORS) → `routers/` (HTTP only) → `security.py` (all crypto, token lifecycle, DB token queries) → `models.py` / `database.py`.

- `security.py` owns every password hash, token issue/validate/revoke, and reset-token operation. New auth logic belongs there, not in routers.
- `schemas.py` holds Pydantic request/response models. Cross-field rules (password confirmation) are `@model_validator(mode="after")`.
- `config.py` exposes a **module-level singleton `settings = Settings()` created at import time.** Setting env vars after importing `app.config` has no effect — this trips up test setup.
- Password reset delivery: in `ENVIRONMENT=local` only, `log_reset_delivery()` logs the URL as `password_reset_dev_delivery url=…`. That log line *is* the delivery channel (ADR-0004).

### Frontend auth: the auth-bridge pattern

`src/lib/api.ts` is deliberately React-free and holds a module-level mutable `authBridge`. `AuthProvider` (`src/lib/auth.tsx`) registers itself into it via `registerAuthBridge()` in an effect. This inversion lets `apiFetchAuth` trigger a token refresh without importing React context.

**Two fetch helpers — picking the wrong one is the most common bug here:**

| Helper | Use for | Behavior |
|--------|---------|----------|
| `apiFetch` | public endpoints (login, register, password reset) | plain fetch, throws `HttpError` |
| `apiFetchAuth` | anything requiring a session | attaches bearer token, on 401 → refresh → retry once → `onAuthFailure` |

**There are two independent refresh paths.** `apiFetchAuth` refreshes through a module-level `refreshMutex`; `performRefresh` in `auth.tsx` (proactive timer, bootstrap, visibility-change) calls `apiFetch` directly and bypasses that mutex. Harmless today because refresh tokens don't rotate — but see `docs/tech-debt.md` before implementing Wave 3 rotation.

### Frontend session lifecycle

- Access token lives **in memory only**; refresh token in `sessionStorage` under `identity_platform_refresh`.
- `authStatus` is tri-state: `loading` | `authenticated` | `anonymous`. `initialAuthStatus()` reads `sessionStorage` synchronously so a page reload with a stored refresh token starts in `loading`, preventing a flash-redirect to `/login` before bootstrap finishes.
- `ProtectedRoute` renders a spinner on `loading` and redirects on `anonymous`.
- Proactive refresh fires `ACCESS_REFRESH_MARGIN_MS` (2 min) before expiry, and on tab re-focus if within that margin.

### Gotcha: SQLite tests vs Postgres runtime

Tests run on in-memory SQLite; production is Postgres. SQLite returns naive datetimes, which is why `security.py` guards every expiry comparison with `if expires.tzinfo is None: expires = expires.replace(tzinfo=UTC)`. Don't remove those guards, and don't trust the test suite to catch Postgres-specific constraint behavior.

### Gotcha: bcrypt's 72-byte password limit

The installed `bcrypt` (5.x) raises `ValueError` instead of truncating when a password exceeds 72 bytes. Any password field (`RegisterRequest.password`, `ChangePasswordRequest.new_password`, `PasswordResetConfirm.new_password`) that reaches `hash_password`/`verify_password`/`verify_password_timing_safe` in `security.py` without a length cap turns a long input into an unhandled `500` instead of a clean `422` (`docs/tech-debt.md` item 24). Any new password field needs the same cap `specs/security/requirements.md` documents.

### Gotcha: `exclude_unset` doesn't distinguish "omitted" from "explicit null"

`ProfileUpdate` fields are `Optional[...] = None` so PATCH can treat an absent field as "leave unchanged" via `body.model_dump(exclude_unset=True)`. But a client that sends the field as JSON `null` looks identical to a client that never included it — both come back as `None` once "set." For a *required* column (`first_name`, `last_name`, `email`) that reaches `setattr` and then the DB's `NOT NULL` constraint, surfacing as a misleading `IntegrityError` → `409` rather than a `422` (`docs/tech-debt.md` item 26). Any new PATCH schema mixing optional-and-unset with required-but-nullable-in-the-request-model needs an explicit guard, not just `exclude_unset`.

## Conventions

- Backend: Ruff, line length 100, target py312.
- Routers stay thin — HTTP concerns only; logic goes to `security.py`.
- Error responses use FastAPI `HTTPException` with a `detail` string; the SPA surfaces `detail` via `HttpError` (`api.ts::parseError`).
- Password reset request always returns the same generic message regardless of whether the account exists (`RESET_MESSAGE` in `routers/auth.py`) — do not add account-enumerating branches.
- Emails are normalized with `normalize_email()` (strip + lowercase) on every write and lookup path.

## Repository state

This directory is **not a git repository** despite containing a `.gitignore`. There is no CI configuration.
