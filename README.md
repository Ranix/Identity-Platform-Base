# Identity Platform

Central identity service for authentication, session management, and user profiles (Spec-Driven Development).

**Current delivery:** [Wave 1 – Local core](specs/product/waves.md#wave-1--local-core)

## Daily reading

Keep these open while implementing Wave 1:

1. [docs/sdd-workflow.md](docs/sdd-workflow.md) — spec-first rules, DoR / DoD  
2. [specs/api/openapi.yaml](specs/api/openapi.yaml) — REST contract  
3. [specs/features/](specs/features/) — active feature (F-001 … F-009; **F-007** / **F-008** when touching SPA session)  
4. [specs/product/waves.md](specs/product/waves.md) — wave scope and completion checklist  

Consult as needed: [docs/vision.md](docs/vision.md), [docs/frontend.md](docs/frontend.md) (SPA architecture), [specs/ux/user-journeys-wave1.md](specs/ux/user-journeys-wave1.md) (journeys + **bug narrative template**), [specs/product/mvp-scope.md](specs/product/mvp-scope.md), [specs/security/](specs/security/), [specs/data/model.md](specs/data/model.md), [adr/](adr/).

## What's in this repository

### Spec-Driven documentation

| Location | Contents |
|----------|----------|
| [docs/vision.md](docs/vision.md) | Vision, principles, tech stack (replaces the early draft `Start` note) |
| [docs/sdd-workflow.md](docs/sdd-workflow.md) | How specs drive implementation (DoR / DoD) |
| [docs/glossary.md](docs/glossary.md) | Terms (SPA, access/refresh token, waves, etc.) |
| [docs/frontend.md](docs/frontend.md) | **SPA guide** — stack, auth, routes, API layer, spec map |
| [specs/product/mvp-scope.md](specs/product/mvp-scope.md) | In/out scope matrix (product MVP vs Wave 1) |
| [specs/product/waves.md](specs/product/waves.md) | Delivery waves and Wave 1 Definition of Done |
| [specs/features/](specs/features/) | Feature specs **F-001** … **F-009** (F-007–F-008 Wave 1 SPA; F-009 Wave 2) |
| [specs/api/openapi.yaml](specs/api/openapi.yaml) | HTTP contract — source of truth for the REST API |
| [specs/security/](specs/security/) | Auth flows, password/token requirements |
| [specs/data/model.md](specs/data/model.md) | Entities: users, refresh tokens, password reset tokens |
| [specs/ux/screens-mvp.md](specs/ux/screens-mvp.md) | SPA routes and mobile-first UX notes |
| [specs/ux/user-journeys-wave1.md](specs/ux/user-journeys-wave1.md) | User journeys, story map, E2E checklist, bug/intent reports |
| [specs/ux/reports/](specs/ux/reports/) | Optional in-repo bug narratives (see journeys doc) |
| [adr/](adr/) | ADRs **0001**–**0004** (SDD process, build vs buy, tokens, reset delivery in local) |

### Backend (`backend/`)

FastAPI application aligned with `specs/api/openapi.yaml`:

- **Auth:** register, login, logout (revokes refresh in DB), refresh access token
- **Profile:** `GET/PATCH /v1/users/me`
- **Passwords:** change (authenticated), reset request + confirm (F-006)
- **Tokens:** short-lived JWT access; opaque refresh stored hashed (see [ADR-0003](adr/0003-mvp-token-session-model.md))
- **Local reset:** reset URL logged as `password_reset_dev_delivery` ([ADR-0004](adr/0004-password-reset-delivery.md))
- **Migrations:** Alembic `alembic/versions/001_initial.py`
- **Tests:** `backend/tests/` (Pytest)

### Frontend (`frontend/`)

Official **SPA** (React, Vite, TypeScript, Tailwind) — mobile-first layout.

**Documentation:** [docs/frontend.md](docs/frontend.md) · **Quick run:** [Frontend SPA](#frontend-spa) below · **In-repo pointer:** [frontend/README.md](frontend/README.md)

- Landing, register, login, forgot/reset password
- Protected: dashboard, profile, security (change password, sign out)
- Auth: access token in memory; refresh in `sessionStorage`; Vite dev proxy to API
- Session client [F-007](specs/features/F-007-spa-session-client.md) and UI polish [F-008](specs/features/F-008-spa-ui-polish.md) implemented in SPA

### Infrastructure

- [docker-compose.yml](docker-compose.yml) — PostgreSQL + API (port **8000**)
- [backend/Dockerfile](backend/Dockerfile), [backend/.env.example](backend/.env.example)

## Quick start (local)

### API + database (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000  
- OpenAPI UI: http://localhost:8000/docs  
- Postgres: `localhost:5432` (user/pass/db: `identity`)

### API (without Docker)

```bash
cd backend
cp .env.example .env
uv sync --extra dev
# Postgres must be running and DATABASE_URL set
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend SPA

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/v1` and `/health` to the API).

### Tests

```bash
cd backend && uv run pytest
```

### Password reset (local)

After requesting reset, check API logs for:

`password_reset_dev_delivery url=http://localhost:5173/reset-password?token=...`

See [ADR-0004](adr/0004-password-reset-delivery.md).

### Cleaning up expired tokens

Expired `refresh_tokens` and `password_reset_tokens` rows are only ever deleted when someone tries to *use* that specific expired row — otherwise they accumulate. Run this manually, or schedule it externally (cron, host timer):

```bash
cd backend
uv run python scripts/cleanup_expired_tokens.py
```

There's no in-process scheduler yet — that's Wave 3 (see `docs/tech-debt.md` item 11).

### Test on your phone (public URL)

Requires Docker Desktop running.

```bash
docker compose up -d --build
./scripts/mobile-public-url.sh
```

The script starts **cloudflared** and prints a `https://*.trycloudflare.com` URL — open it on your phone (cellular or Wi‑Fi). The tunnel forwards to the SPA on port **5173**; API calls go through Vite’s proxy.

For password-reset links in API logs to match the public URL:

```bash
PUBLIC_APP_URL=https://YOUR-TUNNEL.trycloudflare.com CORS_ORIGINS=https://YOUR-TUNNEL.trycloudflare.com docker compose up -d api
```

The tunnel stops when you terminate `cloudflared` (Ctrl+C). Quick tunnels are **dev-only**, not for production.

## Wave 1 status

| Area | Status |
|------|--------|
| SDD specs + OpenAPI | Done |
| Backend API | Implemented |
| SPA screens + F-007 / F-008 | Implemented (run `npm install` + `npm run dev`) |
| Docker Compose | API + Postgres |

**Remaining DoD** (detail in [specs/product/waves.md](specs/product/waves.md)):

- [x] Implement [F-007](specs/features/F-007-spa-session-client.md) and [F-008](specs/features/F-008-spa-ui-polish.md)
- [ ] End-to-end check: Docker + SPA + full auth and reset flow on your machine
- [ ] Stay logged in >15 min on dashboard (proactive refresh or 401 retry)
- [ ] Confirm OpenAPI at `/docs` matches `specs/api/openapi.yaml`
- [ ] Update Wave 1 checkboxes in `specs/product/waves.md` when validated

## Implementing changes

Follow [docs/sdd-workflow.md](docs/sdd-workflow.md): update the feature spec and OpenAPI first, then code.
