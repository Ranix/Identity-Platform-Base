import pytest
from pydantic import ValidationError

from app.config import DEFAULT_JWT_SECRET, Settings
from app.config import settings as global_settings


def test_settings_rejects_default_jwt_secret_outside_local() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret=DEFAULT_JWT_SECRET)


def test_settings_rejects_short_jwt_secret_outside_local() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="too-short")


def test_settings_accepts_strong_jwt_secret_outside_local() -> None:
    strong_secret = "a" * 32
    settings = Settings(environment="production", jwt_secret=strong_secret)
    assert settings.jwt_secret == strong_secret


def test_settings_allows_default_jwt_secret_in_local() -> None:
    settings = Settings(environment="local", jwt_secret=DEFAULT_JWT_SECRET)
    assert settings.jwt_secret == DEFAULT_JWT_SECRET


def test_global_settings_singleton_picked_up_conftest_jwt_secret() -> None:
    """Regression for docs/tech-debt.md item 7: JWT_SECRET must be set in
    tests/conftest.py (imported before any test module), since `settings`
    is a module-level singleton evaluated at `app.config` import time."""
    assert global_settings.jwt_secret == "test-secret-key-at-least-32-characters-long"
