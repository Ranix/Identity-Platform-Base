# Glossary

| Term | Definition |
|------|------------|
| **F-007 / F-008** | Wave 1 SPA specs: session client and UI polish |
| **F-009** | Wave 2 SPA spec: Zod form validation |
| **Identity Platform** | This service; SSOT for user identity in the ecosystem |
| **SPA** | Single Page Application — React client; official Wave 1 consumer |
| **Access token** | Short-lived JWT used on API requests (`Authorization: Bearer`) |
| **Refresh token** | Opaque token stored hashed in DB; used to obtain new access tokens |
| **Session (MVP)** | One refresh token row tied to a user; logout revokes that row |
| **Wave** | Incremental delivery slice with its own DoD |
| **Capability** | Long-lived product ability (may span several waves) |
| **User journey** | Named path through the app (see [user-journeys-wave1.md](../specs/ux/user-journeys-wave1.md)) |
| **Bug narrative** | Numbered steps + journey/step + expected vs actual (for humans and AI context) |
