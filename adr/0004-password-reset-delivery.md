# ADR-0004: Password reset delivery (local vs production)

## Status

Accepted

## Context

Wave 1 includes password reset but no SMTP/SES setup for local iteration. Wave 2 adds real email.

## Decision

- **API behavior** is identical: request creates hashed reset token with expiry; confirm consumes token and updates password.
- **Request response** is always generic (no enumeration).
- **Local (`ENVIRONMENT=local`):** after creating a token, log a single structured line containing the reset URL or raw token for developers (never in production logs).
- **Production (Wave 2+):** send email with link `{PUBLIC_APP_URL}/reset-password?token=...` and disable dev log delivery.

Optional Wave 1 dev-only: include `reset_token` in JSON response **only** when `ENVIRONMENT=local` and `DEV_EXPOSE_RESET_TOKEN=true` — default **false**; prefer logs.

## Consequences

- Developers must read API logs or enable dev flag to complete reset flow locally
- Spec F-006 and SPA must support token via query string on `/reset-password`
- Before prod, Wave 2 enabler replaces delivery channel without changing confirm API shape
