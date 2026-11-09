# Technical debt and improvement backlog

Findings from a full code review of `backend/` and `frontend/` (2026-08-25), against `specs/`, `adr/` and `specs/product/waves.md`. A follow-up independent review on 2026-08-26 re-verified every "Fixed" item below against the running code and test suite (all held) and found 8 new items (24–31).

**Scope note:** items deliberately deferred by the wave plan (email verification, refresh rotation, rate limiting, Zod validation, frontend tests) are **not** listed as debt. Everything below is either a defect, a gap against the Wave 1 Definition of Done, or a decision that will actively hurt a later wave.

Priority: **P1** = fix before closing Wave 1 · **P2** = fix in Wave 2 · **P3** = cleanup, no deadline.

---

## P1 — Security defects

### 1. ~~Changing or resetting a password does not invalidate existing sessions~~ — Fixed 2026-08-25

`backend/app/routers/auth.py` (reset) and `backend/app/routers/users.py` (change) now call `security.revoke_all_refresh_tokens(db, user)` before committing the new password hash, so every refresh token for the account is deleted in the same transaction.

Specs updated accordingly: `specs/features/F-005-change-password.md` (criterion 4) and `specs/features/F-006-password-reset.md` (criterion 3), with the decision recorded in the ADR-0003 addendum. Because `change_password` revokes the session making the request too, `SecurityPage.tsx` now calls `logout()` and redirects to `/login` on success instead of showing an inline message.

Regression tests: `test_change_password_revokes_existing_refresh_tokens`, `test_password_reset_confirm_revokes_existing_refresh_tokens` in `backend/tests/test_auth.py`.

### 2. ~~Password reset consumes the token in a separate transaction from the password update~~ — Fixed 2026-08-25

`consume_password_reset()` no longer commits; `password_reset_confirm` in `routers/auth.py` now performs a single `db.commit()` after marking the token used, hashing the new password, and revoking refresh tokens (item 1). A failure at any point rolls back the whole request — the token is never spent without the password actually changing.

No spec/ADR change needed: `ADR-0004` already frames "confirm consumes token and updates password" as one action, and `F-006`/OpenAPI don't specify transaction boundaries.

Regression test: `test_password_reset_confirm_rolls_back_on_failure_after_token_consumption` in `backend/tests/test_auth.py` (monkeypatches `hash_password` to fail, confirms the token is still valid afterward).

### 3. ~~Login timing leaks whether an account exists~~ — Fixed 2026-08-25

`routers/auth.py::login` now always calls `security.verify_password_timing_safe(password, user.password_hash if user else None)` before checking `user is None`. When the account doesn't exist, the comparison runs against a dummy bcrypt hash precomputed once at import time, so the bcrypt cost is paid on every login attempt regardless of whether the email is registered.

No spec change needed: `F-002` criterion 2 already required a generic *message*; this only closes the timing side-channel the wording didn't explicitly cover.

Regression test: `test_login_with_unknown_email_still_runs_password_check` in `backend/tests/test_auth.py` (spies on `bcrypt.checkpw` to confirm it still runs for an unknown email).

### 4. ~~`JWT_SECRET` falls back to a hardcoded default with no environment guard~~ — Fixed 2026-08-25

`Settings` (`backend/app/config.py`) now has a `@model_validator` that raises at startup when `environment != "local"` and `jwt_secret` is either the repo's placeholder default or under 32 characters — the API refuses to boot instead of running with a publicly known signing key.

Spec updated: added a **Secrets** section to `specs/security/requirements.md`, referencing ADR-0003.

Regression tests: `backend/tests/test_config.py` (accepts/rejects the default and short secrets outside `local`; allows the default in `local`).

**Fix:** add a validator on `Settings` that raises at startup when `environment != "local"` and the secret is the default or shorter than 32 characters.

### 5. ~~Changing the email address preserves `email_verified`~~ — Fixed 2026-08-25

`update_me` (`routers/users.py`) now resets `email_verified` to `False` whenever the PATCH changes `email` to a value different from the current one; profile updates that don't touch `email` (or resubmit the same address) leave the flag untouched.

Specs updated: `F-004` (new criterion 5) and `specs/data/model.md` (`email_verified` row note). No ADR needed — unlike item 1, no existing spec text made this conditional on an ADR update.

Regression tests: `test_email_change_resets_email_verified`, `test_profile_update_without_email_change_keeps_email_verified` in `backend/tests/test_auth.py` (the fixture's `client.session_factory` escape hatch sets `email_verified = True` directly, since no Wave 1 endpoint does).

**Fix:** set `email_verified = False` whenever `email` changes. Worth doing now, while it is a one-line change, rather than discovering it mid-Wave 2.

---

## P1 — Wave 1 Definition of Done gaps

### 6. ~~Test coverage does not meet the stated DoD~~ — Fixed 2026-08-25

`backend/tests/test_auth.py` grew from 2 tests to 22 (plus 4 in `test_config.py` for item 4), closing every gap listed against `waves.md:46` ("Pytest suite passes for auth, profile, password flows") and adding regression coverage for every P1 fix above (items 1–5):

- `POST /v1/auth/refresh` success path — `test_refresh_issues_new_access_token`
- `POST /v1/auth/password-reset/request` anti-enumeration for an unknown email — `test_password_reset_request_unknown_email_returns_generic_message`
- Expired / already-used reset token rejection — `test_password_reset_confirm_expired_token_returns_400`, `test_password_reset_confirm_rejects_reused_token`
- `POST /v1/users/me/password` wrong current password / new-password mismatch — `test_change_password_wrong_current_password_returns_400`, `test_change_password_new_password_mismatch_returns_422`
- `PATCH /v1/users/me` duplicate email → `409` — `test_profile_update_duplicate_email_returns_409`
- Duplicate registration → `409` — `test_register_duplicate_email_returns_409`
- Registration password-confirmation mismatch → `422` — `test_register_password_mismatch_returns_422`
- Login with a wrong password for an existing account → `401` — `test_login_wrong_password_returns_401`

No spec changes needed — every case tests behavior already required by `F-001`, `F-002`, `F-004`, `F-005`, `F-006`.

### 7. ~~The test fixture's `JWT_SECRET` override does nothing~~ — Fixed 2026-08-25

Moved `os.environ.setdefault("JWT_SECRET", ...)` out of the `client` fixture and into `backend/tests/conftest.py`, which pytest imports before collecting any test module — so it now runs before `app.config`'s module-level `settings = Settings()` singleton is evaluated.

Regression test: `test_global_settings_singleton_picked_up_conftest_jwt_secret` in `backend/tests/test_config.py`, which asserts the actual global `settings` object (not a fresh `Settings(...)` call) has the test secret. Verified it fails without the `conftest.py` fix (falls back to `DEFAULT_JWT_SECRET`) before restoring it.

---

## P1 — New defects found in 2026-08-26 follow-up review

### 24. ~~Passwords longer than 72 bytes crash register/login/change-password/reset-confirm with a 500~~ — Fixed 2026-08-27

`backend/app/schemas.py` now defines a shared `BcryptPassword` annotated type (`Annotated[str, AfterValidator(_check_bcrypt_byte_length)]`) that rejects any string whose UTF-8 encoding exceeds 72 bytes with a clean `422`, before it ever reaches bcrypt. Applied to every field that flows into `hash_password`/`verify_password`/`verify_password_timing_safe`: `RegisterRequest.password`, `LoginRequest.password`, `ChangePasswordRequest.current_password` and `.new_password`, `PasswordResetConfirm.new_password`. The `*_confirm` fields (only ever compared for equality, never hashed) were left untouched — no need to guard them.

For login, the byte-length check runs at request validation, before any DB lookup or bcrypt call for either an existing or nonexistent account — so it doesn't reopen the timing side-channel closed by item 3 (both paths short-circuit identically before touching the dummy-hash comparison).

Spec updated: `specs/security/requirements.md` now documents "Maximum length: 72 bytes" alongside the existing minimum. New `CLAUDE.md` gotcha added so any future password field remembers the cap.

Regression tests in `backend/tests/test_auth.py`: `test_register_password_over_72_bytes_returns_422`, `test_login_password_over_72_bytes_returns_422_not_500`, `test_change_password_new_password_over_72_bytes_returns_422`, `test_password_reset_confirm_new_password_over_72_bytes_returns_422`. Also verified against the running app (`uv run uvicorn`) — an 80-character password on `/v1/auth/register` and `/v1/auth/login` (unknown email) now returns `422`, not `500`.

### 25. ~~Users without a phone number can't save any profile changes, and no one can ever clear a saved phone number~~ — Fixed 2026-08-27

Took the "accept `phone: ""` as valid, treat as clear" branch of the two options this item proposed — matches the already-written `specs/features/F-004-profile.md` criterion 7 (`phone: ""` clears the field → `200`), and avoids touching `ProfilePage.tsx`'s full-form-resubmit behavior (a separate, larger change with no other reported problems).

`backend/app/schemas.py`: `PHONE_PATTERN` changed from `{1,32}` to `{0,32}`, so an empty string now passes Pydantic validation instead of getting rejected before `update_me` even runs. `backend/app/routers/users.py::update_me` converts `data["phone"] == ""` to `None` right after `model_dump`, so the DB stores `NULL`, not `""` — consistent with the column already being nullable rather than empty-string-typed.

Regression tests in `backend/tests/test_auth.py`: `test_profile_update_accepts_empty_phone_for_user_without_phone` (PATCH with `{"first_name": ..., "phone": ""}` on an account with no phone on file now returns `200` and updates `first_name`, closing the original failure mode) and `test_profile_update_empty_phone_clears_existing_phone` (PATCH `{"phone": ""}` after setting a real phone number returns `200` with `phone: null`). `test_profile_update_rejects_overlong_phone` still passes unchanged — the pattern's upper bound (32) wasn't touched.

No spec change needed — `specs/features/F-004-profile.md` criterion 7 and `specs/api/openapi.yaml`'s `phone` field already described this exact behavior (added during the 2026-08-26 follow-up review); the fix was making the code match it.

Not verified against a real running Postgres instance — Docker isn't available in this environment (same limitation as item 9). Verified via the SQLite-backed pytest suite only, which is how every other item in this document without a live Postgres was verified.

---

## P2 — Correctness and forward-compatibility

### 8. ~~Two uncoordinated refresh paths will break Wave 3 rotation~~ — Fixed 2026-08-25

`api.ts` now exports its mutex helper as `withRefreshMutex`. `auth.tsx` defines a single `synchronizedRefresh = () => withRefreshMutex(performRefresh)`, and every trigger that can start a refresh — the 401-retry bridge (`authBridge.refreshAccessToken`), the proactive timer, the bootstrap effect, the visibility-change handler, and the public `refreshSession()` — calls `synchronizedRefresh()` instead of `performRefresh()` directly. `apiFetchAuth` no longer wraps `authBridge.refreshAccessToken()` in its own `withRefreshMutex` call, since that callback is already synchronized on its side — double-wrapping the same module-level mutex would have raced the two wrap layers against each other instead of serializing them.

Specs updated: `F-007` criterion under "Automatic retry on 401" now states the mutex is shared by every trigger, and the implementation notes call it out explicitly.

No automated test — this project has no frontend test runner yet (Wave 3, per `waves.md`). Verified by manual trace of the mutex's synchronous assignment order to rule out the double-wrap race described above. `npm install && npm run build` now runs clean (2026-08-25, Node installed) — `tsc -b` and `vite build` both pass, confirming the mutex change type-checks and builds.

While verifying this, `npm run build` failed on an unrelated pre-existing error: `RegisterPage.tsx` imported `Link` from `react-router-dom` but never used it (the page uses `TextLink` instead) — `tsc -b` treats unused imports as errors. Removed the dead import; not a functional change. This had never been caught before because Node/npm was never available in this environment until now.

### 9. ~~`PasswordResetToken.token_hash` lacks the uniqueness constraint its sibling has~~ — Fixed 2026-08-25

`backend/app/models.py` now declares `PasswordResetToken.token_hash` as `unique=True, index=True`, matching `RefreshToken.token_hash`. Migration `backend/alembic/versions/002_password_reset_token_hash_unique.py` drops and recreates `ix_password_reset_tokens_token_hash` as a unique index — not yet applied (no Postgres instance running in this environment); run `alembic upgrade head` against a real database before shipping.

Spec updated: `specs/data/model.md` now lists `password_reset_tokens.token_hash` as `string unique`, matching the `refresh_tokens` row.

No new test added — existing `backend/tests` run on in-memory SQLite via `Base.metadata.create_all`, which already picks up `unique=True` from the model; the 23-test suite still passes.

### 10. ~~Bulk delete without `synchronize_session`~~ — Fixed 2026-08-25

`create_password_reset()` in `backend/app/security.py` now passes `delete(synchronize_session=False)`, matching `revoke_all_refresh_tokens()` (already explicit from the item 1 fix). No spec change needed — this is an internal SQLAlchemy detail, not part of the documented contract.

### 11. ~~Expired tokens are never cleaned up~~ — Fixed 2026-08-25 (manual/cron script; no in-process scheduler)

Added `security.cleanup_expired_tokens(db)` and `backend/scripts/cleanup_expired_tokens.py`, runnable manually (`uv run python scripts/cleanup_expired_tokens.py`) or from an external scheduler (cron, host timer) — documented in the root `README.md`.

Deliberately **not** an in-process scheduler (APScheduler, Celery beat, etc.): Wave 1 has no background-job infrastructure, and `waves.md` already places "Operational runbooks" in Wave 3. A manual/cron-invokable script satisfies the tech-debt item's stated minimum bar ("at minimum a documented manual query") without adding new always-running infrastructure ahead of that wave.

The cleanup compares expiry in Python rather than filtering by `expires_at` in SQL, for the same reason every other expiry check in `security.py` does (SQLite stores naive datetimes in tests, Postgres stores aware ones at runtime).

No spec change needed — no spec documents token-retention/cleanup behavior.

Regression test: `test_cleanup_expired_tokens_deletes_only_expired_rows` in `backend/tests/test_auth.py` (seeds one expired + one live row in each table, asserts only the expired ones are deleted). Also manually verified end-to-end against a real SQLite file (not just the in-memory test DB): seeded an expired and a live refresh token, ran the script, confirmed only the expired one was gone.

### 12. ~~`allow_credentials=True` is unnecessary and widens CORS~~ — Fixed 2026-08-25

Removed `allow_credentials=True` from the `CORSMiddleware` config in `backend/app/main.py` (FastAPI defaults it to `False`). The SPA authenticates with `Authorization` headers, never cookies, so nothing depended on it. No spec change needed — no spec documents CORS behavior.

### 13. ~~Profile fields accept unvalidated free text~~ — Fixed 2026-08-25

`ProfileUpdate` in `backend/app/schemas.py` now constrains all three fields to match the DB column widths and add real format checks:

- `phone`: `max_length=32`, pattern `^[0-9+\-\s()]{1,32}$` (digits, `+`, spaces, dashes, parens)
- `locale`: `max_length=16`, pattern `^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$` (BCP-47-shaped tags, e.g. `en`, `es-MX`)
- `timezone`: `max_length=64`, validated with a `field_validator` against `zoneinfo.available_timezones()` — rejects anything that isn't a real IANA name instead of silently storing garbage a future timezone-aware feature would trip over

An over-long or malformed value now returns a clean `422` instead of reaching the database.

Specs updated: `specs/api/openapi.yaml` (`ProfileUpdate.phone/locale/timezone` gained `maxLength`/`pattern`/description) and `specs/features/F-004-profile.md` (new acceptance criterion 6).

Regression tests in `backend/tests/test_auth.py`: `test_profile_update_rejects_overlong_phone`, `test_profile_update_rejects_overlong_locale`, `test_profile_update_rejects_invalid_timezone`, `test_profile_update_accepts_valid_phone_locale_timezone`.

### 26. ~~`PATCH /v1/users/me` accepts explicit `null` for required fields and reports the wrong error~~ — Fixed 2026-08-27

`update_me` (`backend/app/routers/users.py`) now checks, right after `model_dump(exclude_unset=True)`, whether `first_name`/`last_name`/`email` are present in the diff with value `None` — which can only happen if the client explicitly sent JSON `null` for one of them, since `exclude_unset` already drops fields the client never mentioned. If so, it raises `422` naming the exact field (`"first_name cannot be null"`) before anything reaches `setattr` or the DB, so the misleading `409 Email already in use` from the `IntegrityError` handler can no longer be triggered this way. Left the `IntegrityError` handler itself untouched — with the null case blocked upstream, an actual duplicate-email unique-constraint violation is again the only realistic way to reach it.

Used `status.HTTP_422_UNPROCESSABLE_CONTENT` rather than the older `HTTP_422_UNPROCESSABLE_ENTITY` (Starlette flags the latter as deprecated in the version installed here).

Matches `specs/features/F-004-profile.md` criterion 7 exactly (added during the 2026-08-26 follow-up review): "`422` naming that field — never a `409` or a raw database constraint error." No further spec change needed.

Regression tests in `backend/tests/test_auth.py`: `test_profile_update_explicit_null_first_name_returns_422`, `test_profile_update_explicit_null_email_returns_422_not_409`.

### 27. ~~`login()` can leave the SPA in a half-authenticated state if the post-login profile fetch fails~~ — Fixed 2026-08-27

`login()` in `frontend/src/lib/auth.tsx` now wraps the `GET /v1/users/me` call in a `try/catch`. On failure it calls `await logout()` — the same rollback the bootstrap effect (`useEffect` a few lines down) already used for this exact failure mode — which best-effort-revokes the refresh token server-side, clears `sessionStorage`/in-memory state, cancels the proactive timer, and sets `authStatus` back to `anonymous`, then rethrows the original error so `LoginPage` still shows a message via its existing `catch` block. Chose to mirror the bootstrap effect's established pattern (revoke + rethrow) rather than reordering `applyTokens`/`scheduleProactiveRefresh` to run after the profile fetch, since the codebase already has one correct precedent for this exact race and matching it keeps both call sites consistent.

No spec change needed — `F-007`'s session-client behavior already implies a failed bootstrap/login shouldn't leave a live session; this closes an inconsistency between two code paths, not a new requirement.

No automated test — this project has no frontend test runner yet (Wave 3, per `waves.md`), consistent with how item 8 was verified. `npm run build` and `npm run lint` both pass (no new errors, no new warnings beyond the pre-existing `react-refresh/only-export-components` one). Could not exercise the actual failure path against a live backend — Docker/Postgres aren't available in this environment (same limitation as items 9 and 25); verified by code trace instead: `logout()` is defined earlier in the same file and already handles a missing/expired refresh token gracefully (`if (rt) { ... }` guard), so calling it immediately after `applyTokens` but before any successful profile fetch is safe.

### 28. ~~422 validation errors are never shown as field-specific messages, contradicting screens-mvp.md~~ — Fixed 2026-08-27

`frontend/src/lib/api.ts::parseError` now branches on the shape of `detail`: a string (our own `HTTPException(detail=str)` responses) behaves exactly as before; an array (FastAPI's own `422`s) is mapped into a `FieldError[]` (`{field, message}`, taking `loc.at(-1)` as the field name) and attached to a new `HttpError.fieldErrors` property — the error's top-level `message` becomes the joined field messages, so code that only reads `.message` (unchanged call sites) still gets something readable instead of `res.statusText`.

Added `frontend/src/lib/formErrors.ts::applyFieldErrors(error, setError)` rather than teaching `api.ts` about React Hook Form — `api.ts` is deliberately React-free (see the auth-bridge pattern note in `CLAUDE.md`), and importing RHF's types there would have coupled a framework-agnostic module to a specific form library for no reason. `applyFieldErrors` calls `setError(field, { message })` for each field error and returns whether it applied any, so callers can fall back to the existing root-level banner when the error wasn't a field-shaped `422` (e.g. login's `401`, change-password's `400`).

Wired into all six pages that call `setError("root", ...)` on a caught request error: `RegisterPage`, `LoginPage`, `ProfilePage`, `SecurityPage`, `ForgotPasswordPage`, `ResetPasswordPage`. Each now tries `applyFieldErrors(e, setError)` first and only falls back to the root banner if it returns `false`.

Matches `specs/ux/screens-mvp.md`'s "inline field errors for `422`" requirement; no spec change needed.

No automated test — no frontend test runner yet (Wave 3). Verified the actual response shape against the running backend: `POST /v1/auth/register` with an 80-byte password returns `{"detail":[{"loc":["body","password"],"msg":"Value error, must be at most 72 bytes",...}]}`, confirming `loc.at(-1)` → `"password"` matches the form's field name exactly. `npm run build`, `npm run lint`, and `npm run format:check` all pass clean.

### 29. ~~`/security` screen has no logout control~~ — Fixed 2026-08-27

Added a "Sign out" button to `frontend/src/pages/SecurityPage.tsx`, wired to the same `useLogout()` hook `DashboardPage.tsx` already uses (styling matches too: `PrimaryButton` with the rose destructive-action classes). Sits below the change-password form, outside it, since it's an independent action.

Note this is distinct from the page's existing `logout()` call inside `onSubmit` — that one fires automatically after a successful password change, because the server already revoked every refresh token including this session's (ADR-0003 addendum); the new button is the user-initiated sign-out `screens-mvp.md` calls for regardless of whether they touch the password form at all.

No spec change needed — `specs/ux/screens-mvp.md` already listed "logout" for `/security`; this closes the implementation gap.

No automated test — no frontend test runner yet (Wave 3). Verified `npm run build`, `npm run lint`, and `npm run format:check` all pass clean.

### 30. ~~`password-reset/request` has the same timing side-channel that was fixed for login~~ — Fixed 2026-08-27

Took the "fixed artificial delay" option this item proposed rather than mirroring `create_password_reset`'s exact DB shape (delete + insert + commit) on the not-found path — a dummy `PasswordResetToken` insert isn't possible without a real `user_id` foreign key, and fabricating a sentinel account to insert against would have added more surface area than the leak it closes.

`backend/app/security.py` adds `simulate_password_reset_work()` (a `time.sleep(0.05)` behind a named function, with a comment explaining why it's a delay rather than equivalent DB work) plus a `_DUMMY_RESET_DELAY_SECONDS` constant. `password_reset_request` (`backend/app/routers/auth.py`) now calls it in the `else` branch (user not found), matching the same anti-enumeration intent as `verify_password_timing_safe`'s dummy-hash approach for login (item 3) — same goal, different mechanism, same reason it's necessary.

No spec change needed — `specs/security/requirements.md`'s existing "Generic errors on ... password reset request (no account enumeration on reset)" line already covers this; the fix closes an implementation gap, not a missing requirement.

Regression tests in `backend/tests/test_auth.py`: `test_password_reset_request_unknown_email_still_simulates_reset_work` (monkeypatches `app.security.time.sleep` to a spy, asserts it's called once for an unregistered email) and `test_password_reset_request_known_email_does_not_simulate_reset_work` (same spy, asserts zero calls for a registered email — the real `create_password_reset` path never touches `simulate_password_reset_work`). Tests don't actually sleep, so this adds no measurable time to the suite (40/40 pass).

Not verified by an actual timing measurement against a live Postgres instance — Docker isn't available in this environment (same limitation as items 9, 25, 27). Attempted a `curl`-based timing comparison against a locally running instance first, but discarded it: both requests failed identically with a DB connection error before reaching this code at all (no Postgres running), so it measured nothing. Left as code-level verification (the spy tests above) only.

---

## P3 — Dead code and unused infrastructure

### 14. ~~`DEV_EXPOSE_RESET_TOKEN` is configured but never read~~ — Fixed 2026-08-25

Implemented per its existing spec (ADR-0004 already described this as "Optional Wave 1 dev-only" behavior — it was speced but never wired up, so implementing matched intent better than deleting a decision that was already made). `POST /v1/auth/password-reset/request` now includes `reset_token` in the JSON response, but only when `ENVIRONMENT=local` **and** `DEV_EXPOSE_RESET_TOKEN=true`; otherwise it's `null`, and it's never populated on `/password-reset/confirm`.

Spec updated: `specs/api/openapi.yaml` (`MessageResponse.reset_token`, documented as dev-only/ADR-0004). No ADR change needed — ADR-0004 already specified this exact behavior; the fix was making the code match it.

Regression tests in `backend/tests/test_auth.py`: `test_password_reset_request_does_not_expose_token_by_default`, `test_password_reset_request_exposes_token_when_dev_flag_enabled`.

### 15. ~~React Query is mounted but never used~~ — Fixed 2026-08-25 (dependency removed)

Asked the user to choose between adopting React Query app-wide or dropping it; chose to drop it — the app is small (~430 lines across `pages/`, 2-3 server-state fetches total) and no spec/wave calls for it. Removed `@tanstack/react-query` from `frontend/package.json` and `QueryClientProvider` from `App.tsx` (router tree is now `BrowserRouter > AuthProvider > Routes`). `docs/frontend.md` updated to match. Revisit if manual loading/error handling actually becomes a pain point.

### 16. `zod` and `@hookform/resolvers` are installed but unused

`frontend/package.json` — zero imports. This is F-009 (Wave 2) infrastructure landed early. Already documented in `docs/frontend.md` ("not connected yet ... Wave 2 F-009 infrastructure landed early") so it isn't mistaken for active code — no further action needed; `package.json` itself can't hold comments (JSON has no comment syntax).

### 17. ~~Dead `try/catch` in `login`~~ — Fixed 2026-08-25

Removed the `try { ... } catch (e) { throw e; }` wrapper in `frontend/src/lib/auth.tsx::login` — it caught and immediately re-threw, so callers see identical behavior without it.

### 18. ~~`handleAuthFailure` does a full page reload~~ — Fixed 2026-08-25

`handleAuthFailure` in `frontend/src/lib/auth.tsx` now calls React Router's `navigate("/login", { replace: true })` instead of `window.location.href = "/login"`. Works because `AuthProvider` renders inside `BrowserRouter` (see item 15's tree change), so `useNavigate()` is available. Scope kept to the stated fix (no full reload) — did not add "return to where you were after re-login" (redirect-back), since that's a separate feature not requested here.

Verified with `npm run build` (passes, bundle size dropped ~29KB gzipped confirming React Query was actually removed) and a manual backend+frontend dev-server smoke run (registered a user, confirmed `/health` and the SPA both serve).

**Manual browser click-through completed 2026-08-29** (by the user, no browser automation tool available in this environment): revoked a live refresh token server-side via `curl /v1/auth/logout` while the SPA tab stayed open with `ACCESS_TOKEN_EXPIRE_MINUTES` temporarily lowered to force expiry quickly, then triggered an authenticated request without reloading the tab. Confirmed in Network that landing on `/login` produced no "document" navigation entry (no `index.html`/asset refetch) and the transition was instant, with no full-page flash — the `navigate()` fix behaves as intended for a genuine 401-after-failed-refresh case, not just for a same-tab reload. Item 18 is now fully verified.

---

## P3 — Tooling and process

### 19. The project is not under version control

There is a `.gitignore`, four ADRs, and an SDD workflow that talks about work "merging" — but no git repository. Every code review, rollback, and history question is currently impossible. **This is the highest-leverage item in this document despite its P3 label**, because it costs minutes and everything else becomes safer once it's done.

### 20. No CI

No `.github/` directory. Nothing runs `pytest`, `ruff`, or `tsc -b` automatically. Once git exists, a minimal workflow running those three commands covers most of the risk.

### 21. ~~No linter or formatter on the frontend~~ — Fixed 2026-08-26

Added ESLint (flat config, `frontend/eslint.config.js`) and Prettier (`.prettierrc.json`, `.prettierignore`), plus `lint` / `format` / `format:check` scripts in `frontend/package.json`. Rule set: `@eslint/js` recommended, `typescript-eslint` recommended, `eslint-plugin-react-hooks`'s classic `rules-of-hooks`/`exhaustive-deps` rules only, `eslint-plugin-react-refresh`, with `eslint-config-prettier` disabling any formatting-related rules so ESLint and Prettier never fight.

Deliberately did **not** adopt `eslint-plugin-react-hooks`'s v7 `recommended` config — it now bundles React Compiler-oriented rules (`immutability`, `incompatible-library`, `purity`, etc.) which flagged idiomatic React 18 patterns already in the codebase (e.g. the recursive `scheduleProactiveRefresh` timer in `auth.tsx`) as errors. This app has no React Compiler in its build, so those rules were pure noise for this fix's scope; pinned to the two classic hook rules instead.

`npm run format` reformatted 8 files (whitespace/quoting only, no logic changes); `npm run build` still passes after. One pre-existing warning remains: `react-refresh/only-export-components` on `auth.tsx` for exporting both `AuthProvider` and `useAuth()` — expected for the auth-bridge pattern documented in `CLAUDE.md`, left as a warning rather than suppressed or fixed.

No spec change needed — tooling config, not documented behavior.

### 22. ~~`frontend/` has no `.dockerignore`~~ — Fixed 2026-08-26

Added `frontend/.dockerignore` (`node_modules`, `dist`, `.git`, `*.local`, `tsconfig.tsbuildinfo`), matching the pattern of `backend/.dockerignore`. `Dockerfile:7`'s `COPY . .` no longer copies a local `node_modules/` (host-platform binaries, stale deps) or build output into the image — `npm install` inside the container is now the only source of `node_modules`.

No spec change needed — build tooling, not documented behavior.

### 23. ~~Migrations run on every container start~~ — Noted 2026-08-26 (deferred to Wave 3)

No Wave 3 runbook exists yet to note this in — "Operational runbooks" is itself a Wave 3 deliverable (`waves.md`), so writing one now would be scope creep ahead of that wave's infrastructure. Instead, added a comment directly at `backend/scripts/start.sh:4-5` documenting the constraint (safe with one replica; races with concurrent `alembic upgrade head` calls across multiple replicas) so it surfaces at the point of change rather than depending on a future doc being read. Revisit when Wave 3 introduces multi-replica deploys and an actual runbook.

No spec change needed — deployment tooling, not documented behavior.

### 31. ~~`update_me` doesn't strip whitespace from `first_name`/`last_name`~~ — Fixed 2026-08-27

`update_me` (`backend/app/routers/users.py`) now strips both `first_name` and `last_name` when present in the PATCH diff, right after the item 26 null-check (which guarantees they're real strings, not `None`, by that point) and before `setattr`. Matches `register`'s existing `.strip()` behavior exactly — including its pre-existing limitation that a whitespace-only input (e.g. `"   "`) passes Pydantic's `min_length=1` before stripping and can still end up stored as `""`; fixing that edge case wasn't part of what this item asked for, so left it alone for parity rather than making `update_me` stricter than `register`.

No spec change needed — internal consistency between two code paths, not a documented behavior change.

Regression test in `backend/tests/test_auth.py`: `test_profile_update_strips_whitespace_from_names` (PATCH with `"  Ada  "`/`"  Lovelace  "` returns them trimmed).

---

## New defects found during manual test pass (2026-08-29)

### 32. ~~A whitespace-only name could be saved as a blank string~~ — Fixed 2026-08-29

Found during the manual click-through of item 18: typing only spaces into "First name" on `/profile` saved successfully with a blank name. Root cause is the exact edge case flagged (and deliberately deferred) in item 31's writeup — `Field(min_length=1)` validates the *raw* input before stripping, so `"   "` (length 3) passes, and stripping it afterward silently produces `""`. The same flaw existed in `register`, since `update_me`'s `.strip()` was explicitly written to match `register`'s pre-existing behavior.

`backend/app/schemas.py` adds a `NonBlankName` annotated type (`Annotated[str, AfterValidator(_strip_and_require_nonblank)]`) that strips and re-checks for a non-empty result *after* the `Field(min_length=1, max_length=100)` constraint already ran — closing exactly the gap that constraint alone couldn't catch. Applied to `RegisterRequest.first_name`/`.last_name` and `ProfileUpdate.first_name`/`.last_name`. Since the schema now returns the already-stripped string, removed the now-redundant manual `.strip()` calls from both `routers/auth.py::register` and `routers/users.py::update_me` (the latter was item 31's own fix) — one validator, not duplicated stripping logic in two routers.

Doesn't conflict with item 26 (`null` rejection for required `ProfileUpdate` fields): `NonBlankName | None` still lets an omitted/explicit-`None` field pass through to that separate check untouched, since `AfterValidator` only runs on the `str` branch of the union.

No spec change needed — `specs/features/F-004-profile.md` and `F-001` already imply a "first/last name" is a non-empty value; this closes an implementation gap, not a missing requirement.

Regression tests in `backend/tests/test_auth.py`: `test_register_whitespace_only_first_name_returns_422`, `test_profile_update_whitespace_only_first_name_returns_422`.

### 33. ~~Timezone field required exact free-text IANA names with no guidance~~ — Fixed 2026-08-29

Also found during manual testing: `specs/features/F-004-profile.md`'s timezone validation was always correct (rejects anything not in `zoneinfo.available_timezones()`), but `ProfilePage.tsx` exposed it as a plain `<input>` — a real user has no way to know they must type `"America/Mexico_City"` and not `"CDMX"` or `"GMT-6"`, so they could get stuck unable to save a profile at all.

`frontend/src/pages/ProfilePage.tsx` now renders a `<select>` populated from `Intl.supportedValuesOf("timeZone")` — a browser-native API backed by the same IANA tz database the backend's `zoneinfo.available_timezones()` reads from, so the two lists stay in sync without maintaining a duplicate one in the frontend. Falls back to the previous free-text `<input>` when `Intl.supportedValuesOf` isn't available (older browsers), still validated server-side either way.

No spec change needed — this is a client-side presentation choice; the validation contract `F-004-profile.md` describes didn't change.

No automated test — no frontend test runner yet (Wave 3). Verified `npm run build`, `npm run lint`, and `npm run format:check` all pass clean, and confirmed in Node that `Intl.supportedValuesOf("timeZone")` returns 418 zones including `"America/Mexico_City"`, matching what the backend accepts.

### 34. ~~`/profile`'s "Saved." confirmation never actually appeared~~ — Fixed 2026-08-29

Found while reviewing `/profile` UX: after a successful save, the page gave no visible feedback — felt like the form did nothing. Root cause: the "Saved." message was gated on React Hook Form's `formState.isSubmitSuccessful`, but `onSubmit`'s `setUser(updated)` changes the `user` object from `useAuth()`, which re-triggers `ProfilePage`'s own `useEffect(() => { if (user) reset(user); }, [user, reset])` — and RHF's `reset()` clears `isSubmitSuccessful` back to `false` as part of what it resets. Both happen in the same update cycle, so the confirmation flashed and vanished before it was ever visible.

`frontend/src/pages/ProfilePage.tsx` now tracks a local `justSaved` state instead, set to `true` right after `setUser(updated)` succeeds and reset to `false` at the start of every submit — unaffected by the `reset(user)` effect since it isn't part of RHF's form state.

While in the same file, also added two smaller UX fixes suggested during manual review (not separate backlog items, bundled here since they touched the same component in the same pass):
- `Phone` and `Locale` inputs now have example placeholders (`+1 555 123 4567`, `en or es-MX`) instead of no hint about the expected format.
- `first_name`/`last_name` now validate client-side (`v.trim().length > 0`) before submit, giving instant feedback for the same blank-after-trim case item 32 closed server-side — instead of a round-trip to discover it.

No spec change needed — UI feedback and client-side validation, not a documented API contract change.

No automated test — no frontend test runner yet (Wave 3). Verified `npm run build`, `npm run lint`, and `npm run format:check` all pass clean.

### 35. ~~Same UX gaps existed across the other forms, not just `/profile`~~ — Fixed 2026-08-29

Auditing every form after items 32–34 turned up the same two problems repeated elsewhere:

**Silent required fields.** `SecurityPage.tsx`'s `current_password`, `new_password`, and `new_password_confirm`, and `ProfilePage.tsx`'s `email`, all used React Hook Form's `required: true` (boolean) instead of a message string. RHF still blocks submission either way, but with a boolean it sets the field's error message to an empty string — and `Field`'s `{error ? <span>...</span> : null}` renders nothing for `""`, so leaving one of these blank submitted silently with no visible reason why. Changed all four to `required: "Required"`, matching every other field in the app.

**No client-side mirror of two server rules**, so a real user could type something invalid and only find out after a round-trip:
- Extracted `frontend/src/lib/validators.ts` (`isWithinBcryptByteLimit`, `isNonBlank`) so the checks live in one place instead of being copy-pasted per page.
- `isWithinBcryptByteLimit` (mirrors item 24's 72-byte bcrypt cap) added to every field where a user *sets a new password*: `RegisterPage.password`, `SecurityPage.new_password`, `ResetPasswordPage.new_password`. Deliberately **not** added to `LoginPage.password` — a real login password can never exceed 72 bytes (it was capped at that limit when it was set), so the only way to trigger it there is deliberately hostile input, not a genuine user mistake worth a friendlier client-side message for.
- `isNonBlank` (mirrors item 32's whitespace-only-name check) added to `RegisterPage.first_name`/`.last_name`, alongside `ProfilePage`'s existing usage (refactored to call the shared helper instead of its own inline `v.trim().length > 0`).

Spec updated: `specs/features/F-009-spa-form-validation.md` (already the feature spec covering "consistent client-side validation that matches server rules") gained acceptance criteria 4–5 formalizing the two conventions this item applied — required fields must use a message string, and any server rule the client can cheaply replicate should be mirrored via `frontend/src/lib/validators.ts` — plus a note that criterion 3 (422 → field mapping) was already implemented in Wave 1 via item 28's `applyFieldErrors`, ahead of the Zod migration (criteria 1–2, still Wave 2). Chose `specs/features/` over `CLAUDE.md` for this because `CLAUDE.md`'s own header scopes it as guidance for Claude Code specifically — a convention meant to bind any developer or tool working on this codebase belongs in the project's actual source of truth. `docs/frontend.md`'s roadmap table updated to match.

No automated test — no frontend test runner yet (Wave 3). Verified `npm run build`, `npm run lint`, and `npm run format:check` all pass clean across every changed file.

---

## Suggested order

1. Item 19 (git) — unblocks safe iteration on everything else
2. Items 1, 2, 3, 4, 5 — security defects, with the tests from item 6 written alongside
3. Items 6, 7 — close the Wave 1 DoD
4. Item 8 — before any Wave 3 rotation work begins
5. Item 20 — CI to keep the above from regressing
6. ~~Items 24, 25~~ — Fixed 2026-08-27
7. ~~Items 26–31~~ — Fixed 2026-08-27
8. ~~Item 18~~ — manual click-through completed 2026-08-29
9. ~~Items 32, 33~~ — found during that same manual pass, Fixed 2026-08-29. What's left: item 19 (git), item 20 (CI, depends on 19)
