# ADR-0002: Build custom identity service (Wave 1)

## Status

Accepted

## Context

Ecosystem needs a shared identity SSOT. Managed options (Cognito, Auth0, Keycloak-as-a-service) reduce build cost but add vendor coupling and learning goals differ.

## Decision

Build **Identity Platform** in-house for Wave 1–3 with a path to OAuth2/OIDC (Wave 4). Revisit build vs buy before production traffic if compliance or cost demands it.

## Consequences

- We own security patches, token design, and uptime
- Must follow OWASP auth guidance and keep specs/ADRs current
- Migration to managed IdP later requires ADR and migration plan
