import os

# Must run before any test module imports `app.main` / `app.config`, since
# `settings = Settings()` is a module-level singleton evaluated at import
# time — setting this inside a fixture is too late (docs/tech-debt.md item 7).
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-characters-long")
