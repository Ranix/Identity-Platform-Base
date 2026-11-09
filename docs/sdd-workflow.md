# SDD Workflow

## Principles

1. Every capability has a **feature spec** under `specs/features/` before backend or frontend work merges.
2. The **HTTP contract** lives in `specs/api/openapi.yaml`. If code and OpenAPI disagree, fix code or update OpenAPI with an explicit version/changelog — never silent drift.
3. **ADRs** capture architectural choices that are hard to reverse (tokens, email, build vs buy).
4. Delivery is split into **waves** (`specs/product/waves.md`); DoD applies per wave.

## Artifact states

| State | Meaning |
|-------|---------|
| `draft` | Work in progress, not for implementation |
| `approved` | Ready to implement |
| `implemented` | Done for the current wave; spec kept as regression reference |

Wave 1 feature specs **F-001 … F-008** and OpenAPI are **approved**. **F-009** is approved for Wave 2.

## Implementation order (Wave 1)

1. Data model (`specs/data/model.md`) + migrations
2. Auth & tokens (`F-002`, `F-003`, ADR-0003)
3. Registration (`F-001`)
4. Profile (`F-004`)
5. Change password (`F-005`)
6. Password reset (`F-006`, ADR-0004)
7. SPA screens (`specs/ux/screens-mvp.md`) — F-001…F-006 flows
8. **SPA session client** (`F-007`) — required for usable sessions past access TTL
9. **SPA UI polish** (`F-008`)
10. Docker Compose + README runbook

## Implementation order (Wave 2+)

- Wave 2: identity hardening + **F-009** (Zod)
- Wave 3: infra, refresh rotation, **frontend Vitest + Playwright**

## Definition of Ready (before coding a feature)

- Feature spec `approved`
- OpenAPI paths for the feature exist (backend features); SPA-only features reference existing endpoints
- Security requirements referenced (`specs/security/`) when auth-related

## Definition of Done (Wave 1)

See [specs/product/waves.md#wave-1--definition-of-done](specs/product/waves.md).
