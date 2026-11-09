# Data model (Wave 1)

## Entity: `users`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | string unique | normalized lowercase |
| password_hash | string | |
| first_name | string | |
| last_name | string | |
| phone | string nullable | |
| locale | string | default `en` |
| timezone | string | default `UTC` |
| email_verified | boolean | default `false`; login allowed in Wave 1; reset to `false` whenever `email` changes (F-004) |
| created_at | timestamptz | |
| updated_at | timestamptz | |

## Entity: `refresh_tokens`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | FK users | |
| token_hash | string unique | hash of opaque refresh |
| expires_at | timestamptz | |
| created_at | timestamptz | |

One row per issued refresh in Wave 1 (multiple logins = multiple rows allowed).

## Entity: `password_reset_tokens`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | FK users | |
| token_hash | string unique | |
| expires_at | timestamptz | |
| used_at | timestamptz nullable | set on successful reset |
| created_at | timestamptz | |

Invalidate previous unused tokens for same user on new request (optional but recommended).

## ER (logical)

```
users 1 --- * refresh_tokens
users 1 --- * password_reset_tokens
```
