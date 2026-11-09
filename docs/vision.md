# Identity Platform — Vision

> **Version:** 0.2  
> **Status:** Approved (Wave 1 baseline)  
> **Architecture:** Spec-Driven Development (SDD)

## Vision

Identity Platform is the central service for user identity across the application ecosystem.

It provides reusable authentication, session management, and profile administration so future applications do not reimplement user management.

Identity Platform is the **single source of truth** for user identity.

## SDD philosophy

- Functionality starts in **specs** (`specs/features/`, `specs/api/openapi.yaml`) before code.
- Architecture choices use **ADRs** (`adr/`).
- Code stays aligned with approved specs; OpenAPI is the HTTP contract source of truth.

See [sdd-workflow.md](sdd-workflow.md).

## Goals

**Primary:** Build a reusable identity platform for future projects.

**Specific:**

- Centralize authentication and user administration
- Avoid duplicated user data across apps
- Expose a clear, versioned REST API (`/v1/...`)
- Scale operationally; evolve toward OAuth2/OpenID Connect (Wave 4)

## Wave 1 scope

First iteration is **local** via Docker Compose. Details: [specs/product/waves.md](../specs/product/waves.md).

Email is stored at registration; **email verification is Wave 2**. Password reset is in Wave 1 with **local token delivery** (ADR-0004).

## Responsibilities

- Users, credentials, sessions (refresh in DB)
- JWT access tokens; refresh issuance and validation
- Profile and password flows
- Email verification (Wave 2+)
- Roles/permissions (Wave 4)

## Non-responsibilities

Identity Platform does **not** own product catalog, orders, billing, business notifications, file storage, or other apps’ domain logic.

## Clients

- **Wave 1:** Official **SPA** (React, Vite) — responsive, **mobile-first** presentation. No native app in Wave 1.
- **Future:** Other clients via OAuth2/OIDC.

## Mobile-first principles

- Simple UI, small payloads, fast APIs
- Security by design (see `specs/security/`)
- Responsive layout; primary UX targets phone-sized viewports

## Architecture (logical)

```
React SPA (mobile-first)
        │ HTTPS (local: HTTP)
        ▼
FastAPI — Identity API
        │
   PostgreSQL (users, refresh tokens, reset tokens)
```

JWT signing and validation are **inside the API process** in Wave 1 (not a separate microservice).

## Frontend role

1. Public landing
2. Official client for register, login, dashboard, profile, security

Not a business application.

## Technology

**Backend:** Python 3.12+, FastAPI, SQLAlchemy, Alembic, Pydantic v2, PostgreSQL, uv, Pytest, Ruff  

**Frontend:** React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, React Hook Form

## Future

Shared identity for all ecosystem apps; business logic stays in each app; identity decoupled via API (later OIDC).
