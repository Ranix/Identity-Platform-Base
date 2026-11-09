import logging
import re
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, PasswordResetToken, RefreshToken, User
from app.security import cleanup_expired_tokens

SQLALCHEMY_DATABASE_URL = "sqlite://"


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.session_factory = TestingSessionLocal  # test-only escape hatch for direct DB setup
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_register_login_profile(client: TestClient) -> None:
    reg = client.post(
        "/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )
    assert reg.status_code == 201

    login = client.post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    body = {
        "email": "dup@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "first_name": "First",
        "last_name": "User",
    }
    first = client.post("/v1/auth/register", json=body)
    assert first.status_code == 201

    second = client.post("/v1/auth/register", json={**body, "first_name": "Second"})
    assert second.status_code == 409


def test_register_password_mismatch_returns_422(client: TestClient) -> None:
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "mismatch@example.com",
            "password": "password123",
            "password_confirm": "different456",
            "first_name": "First",
            "last_name": "User",
        },
    )
    assert res.status_code == 422


def test_register_whitespace_only_first_name_returns_422(client: TestClient) -> None:
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "blank-name@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "   ",
            "last_name": "User",
        },
    )
    assert res.status_code == 422


def test_register_password_over_72_bytes_returns_422(client: TestClient) -> None:
    long_password = "a" * 73
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "long-pw@example.com",
            "password": long_password,
            "password_confirm": long_password,
            "first_name": "First",
            "last_name": "User",
        },
    )
    assert res.status_code == 422


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "wrong-pw@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "First",
            "last_name": "User",
        },
    )
    res = client.post(
        "/v1/auth/login",
        json={"email": "wrong-pw@example.com", "password": "not-the-password"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_login_password_over_72_bytes_returns_422_not_500(client: TestClient) -> None:
    long_password = "a" * 73
    res = client.post(
        "/v1/auth/login",
        json={"email": "no-such-account@example.com", "password": long_password},
    )
    assert res.status_code == 422


def test_email_change_resets_email_verified(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "verify-me@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Marie",
            "last_name": "Curie",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "verify-me@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # No Wave 1 endpoint flips email_verified to True — set it directly to
    # simulate an account already verified under Wave 2.
    db = client.session_factory()
    user = db.query(User).filter(User.email == "verify-me@example.com").first()
    user.email_verified = True
    db.commit()
    db.close()

    patch = client.patch(
        "/v1/users/me",
        json={"email": "new-address@example.com"},
        headers=headers,
    )
    assert patch.status_code == 200
    assert patch.json()["email_verified"] is False


def test_profile_update_without_email_change_keeps_email_verified(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "stays-verified@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Marie",
            "last_name": "Curie",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "stays-verified@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    db = client.session_factory()
    user = db.query(User).filter(User.email == "stays-verified@example.com").first()
    user.email_verified = True
    db.commit()
    db.close()

    patch = client.patch("/v1/users/me", json={"first_name": "Marie-Anne"}, headers=headers)
    assert patch.status_code == 200
    assert patch.json()["email_verified"] is True


def _register_and_login(client: TestClient, email: str) -> dict:
    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )
    login = client.post("/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_profile_update_rejects_overlong_phone(client: TestClient) -> None:
    headers = _register_and_login(client, "overlong-phone@example.com")
    patch = client.patch("/v1/users/me", json={"phone": "1" * 33}, headers=headers)
    assert patch.status_code == 422


def test_profile_update_rejects_overlong_locale(client: TestClient) -> None:
    headers = _register_and_login(client, "overlong-locale@example.com")
    patch = client.patch("/v1/users/me", json={"locale": "en-" + "x" * 20}, headers=headers)
    assert patch.status_code == 422


def test_profile_update_rejects_invalid_timezone(client: TestClient) -> None:
    headers = _register_and_login(client, "bad-timezone@example.com")
    patch = client.patch("/v1/users/me", json={"timezone": "Not/A_Real_Zone"}, headers=headers)
    assert patch.status_code == 422


def test_profile_update_accepts_valid_phone_locale_timezone(client: TestClient) -> None:
    headers = _register_and_login(client, "valid-profile-fields@example.com")
    patch = client.patch(
        "/v1/users/me",
        json={"phone": "+1 (555) 123-4567", "locale": "es-MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["phone"] == "+1 (555) 123-4567"
    assert body["locale"] == "es-MX"
    assert body["timezone"] == "America/Mexico_City"


def test_profile_update_accepts_empty_phone_for_user_without_phone(client: TestClient) -> None:
    headers = _register_and_login(client, "no-phone@example.com")
    patch = client.patch(
        "/v1/users/me", json={"first_name": "Renamed", "phone": ""}, headers=headers
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["first_name"] == "Renamed"
    assert body["phone"] is None


def test_profile_update_empty_phone_clears_existing_phone(client: TestClient) -> None:
    headers = _register_and_login(client, "clear-phone@example.com")
    client.patch("/v1/users/me", json={"phone": "+1 (555) 123-4567"}, headers=headers)

    patch = client.patch("/v1/users/me", json={"phone": ""}, headers=headers)
    assert patch.status_code == 200
    assert patch.json()["phone"] is None


def test_profile_update_explicit_null_first_name_returns_422(client: TestClient) -> None:
    headers = _register_and_login(client, "null-first-name@example.com")
    patch = client.patch("/v1/users/me", json={"first_name": None}, headers=headers)
    assert patch.status_code == 422
    assert patch.json()["detail"] == "first_name cannot be null"


def test_profile_update_explicit_null_email_returns_422_not_409(client: TestClient) -> None:
    headers = _register_and_login(client, "null-email@example.com")
    patch = client.patch("/v1/users/me", json={"email": None}, headers=headers)
    assert patch.status_code == 422
    assert patch.json()["detail"] == "email cannot be null"


def test_profile_update_whitespace_only_first_name_returns_422(client: TestClient) -> None:
    headers = _register_and_login(client, "blank-profile-name@example.com")
    patch = client.patch("/v1/users/me", json={"first_name": "   "}, headers=headers)
    assert patch.status_code == 422


def test_profile_update_strips_whitespace_from_names(client: TestClient) -> None:
    headers = _register_and_login(client, "whitespace-name@example.com")
    patch = client.patch(
        "/v1/users/me", json={"first_name": "  Ada  ", "last_name": "  Lovelace  "}, headers=headers
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"


def test_profile_update_duplicate_email_returns_409(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "taken@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Has",
            "last_name": "TheEmail",
        },
    )
    client.post(
        "/v1/auth/register",
        json={
            "email": "wants-it@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Wants",
            "last_name": "TheEmail",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "wants-it@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patch = client.patch("/v1/users/me", json={"email": "taken@example.com"}, headers=headers)
    assert patch.status_code == 409


def test_login_with_unknown_email_still_runs_password_check(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for docs/tech-debt.md item 3: an unknown email must not
    short-circuit before the bcrypt comparison, or response timing leaks
    whether the account exists."""
    original_checkpw = bcrypt.checkpw
    calls: list[tuple[bytes, bytes]] = []

    def spy_checkpw(password: bytes, hashed: bytes) -> bool:
        calls.append((password, hashed))
        return original_checkpw(password, hashed)

    monkeypatch.setattr("app.security.bcrypt.checkpw", spy_checkpw)

    res = client.post(
        "/v1/auth/login",
        json={"email": "no-such-user@example.com", "password": "whatever123"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"
    assert len(calls) == 1


def test_logout_revokes_refresh(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "logout@example.com", "password": "password123"},
    )
    refresh = login.json()["refresh_token"]
    out = client.post("/v1/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 204
    again = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert again.status_code == 401


def test_refresh_issues_new_access_token(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "refresh-me@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "refresh-me@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["refresh_token"] == refresh_token
    assert body["expires_in"] > 0

    me = client.get("/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "refresh-me@example.com"


def test_change_password_revokes_existing_refresh_tokens(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "change-pw@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "change-pw@example.com", "password": "password123"},
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    change = client.post(
        "/v1/users/me/password",
        json={
            "current_password": "password123",
            "new_password": "newpassword456",
            "new_password_confirm": "newpassword456",
        },
        headers=headers,
    )
    assert change.status_code == 204

    again = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_change_password_wrong_current_password_returns_400(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "wrong-current@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "wrong-current@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    change = client.post(
        "/v1/users/me/password",
        json={
            "current_password": "not-the-current-password",
            "new_password": "newpassword456",
            "new_password_confirm": "newpassword456",
        },
        headers=headers,
    )
    assert change.status_code == 400


def test_change_password_new_password_mismatch_returns_422(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "new-pw-mismatch@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "new-pw-mismatch@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    change = client.post(
        "/v1/users/me/password",
        json={
            "current_password": "password123",
            "new_password": "newpassword456",
            "new_password_confirm": "different789",
        },
        headers=headers,
    )
    assert change.status_code == 422


def test_change_password_new_password_over_72_bytes_returns_422(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "long-new-pw@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "long-new-pw@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    long_password = "a" * 73
    change = client.post(
        "/v1/users/me/password",
        json={
            "current_password": "password123",
            "new_password": long_password,
            "new_password_confirm": long_password,
        },
        headers=headers,
    )
    assert change.status_code == 422


def test_password_reset_confirm_revokes_existing_refresh_tokens(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "reset-pw@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Grace",
            "last_name": "Hopper",
        },
    )
    login = client.post(
        "/v1/auth/login",
        json={"email": "reset-pw@example.com", "password": "password123"},
    )
    old_refresh = login.json()["refresh_token"]

    with caplog.at_level(logging.WARNING):
        req = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "reset-pw@example.com"},
        )
    assert req.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    reset_token = match.group(1)

    confirm = client.post(
        "/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "newpassword456",
            "new_password_confirm": "newpassword456",
        },
    )
    assert confirm.status_code == 200

    again = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert again.status_code == 401


def test_password_reset_confirm_rolls_back_on_failure_after_token_consumption(
    client: TestClient, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "atomic-reset@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Atomic",
            "last_name": "Reset",
        },
    )

    with caplog.at_level(logging.WARNING):
        req = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "atomic-reset@example.com"},
        )
    assert req.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    reset_token = match.group(1)

    def boom(_password: str) -> str:
        raise RuntimeError("simulated failure between token consumption and commit")

    monkeypatch.setattr("app.routers.auth.hash_password", boom)

    with pytest.raises(RuntimeError):
        client.post(
            "/v1/auth/password-reset/confirm",
            json={
                "token": reset_token,
                "new_password": "newpassword456",
                "new_password_confirm": "newpassword456",
            },
        )

    monkeypatch.undo()

    # Token must still be usable: the failed attempt must not have left it
    # marked as consumed without also applying the password change.
    retry = client.post(
        "/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "newpassword456",
            "new_password_confirm": "newpassword456",
        },
    )
    assert retry.status_code == 200


def test_password_reset_request_unknown_email_returns_generic_message(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        res = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "never-registered@example.com"},
        )
    assert res.status_code == 200
    assert res.json()["message"] == (
        "If an account exists for this email, reset instructions have been sent."
    )
    assert "password_reset_dev_delivery" not in caplog.text


def test_password_reset_request_unknown_email_still_simulates_reset_work(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(
        "app.security.time.sleep", lambda seconds: calls.append(seconds)
    )

    res = client.post(
        "/v1/auth/password-reset/request",
        json={"email": "never-registered-again@example.com"},
    )
    assert res.status_code == 200
    assert len(calls) == 1


def test_password_reset_request_known_email_does_not_simulate_reset_work(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "known-reset-timing@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    calls = []
    monkeypatch.setattr(
        "app.security.time.sleep", lambda seconds: calls.append(seconds)
    )

    with caplog.at_level(logging.WARNING):
        res = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "known-reset-timing@example.com"},
        )
    assert res.status_code == 200
    assert len(calls) == 0


def test_password_reset_request_does_not_expose_token_by_default(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "no-dev-flag@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "No",
            "last_name": "Flag",
        },
    )
    with caplog.at_level(logging.WARNING):
        res = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "no-dev-flag@example.com"},
        )
    assert res.status_code == 200
    assert res.json()["reset_token"] is None


def test_password_reset_request_exposes_token_when_dev_flag_enabled(
    client: TestClient, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.routers.auth.settings.dev_expose_reset_token", True)
    client.post(
        "/v1/auth/register",
        json={
            "email": "dev-flag@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Dev",
            "last_name": "Flag",
        },
    )
    with caplog.at_level(logging.WARNING):
        res = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "dev-flag@example.com"},
        )
    assert res.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    assert res.json()["reset_token"] == match.group(1)


def test_password_reset_confirm_new_password_over_72_bytes_returns_422(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "long-reset-pw@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    with caplog.at_level(logging.WARNING):
        req = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "long-reset-pw@example.com"},
        )
    assert req.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    reset_token = match.group(1)

    long_password = "a" * 73
    confirm = client.post(
        "/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": long_password,
            "new_password_confirm": long_password,
        },
    )
    assert confirm.status_code == 422


def test_password_reset_confirm_expired_token_returns_400(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "expired-reset@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    with caplog.at_level(logging.WARNING):
        req = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "expired-reset@example.com"},
        )
    assert req.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    reset_token = match.group(1)

    db = client.session_factory()
    row = (
        db.query(PasswordResetToken)
        .join(User)
        .filter(User.email == "expired-reset@example.com")
        .first()
    )
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    db.close()

    confirm = client.post(
        "/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "newpassword456",
            "new_password_confirm": "newpassword456",
        },
    )
    assert confirm.status_code == 400


def test_password_reset_confirm_rejects_reused_token(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "reuse-reset@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    with caplog.at_level(logging.WARNING):
        req = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "reuse-reset@example.com"},
        )
    assert req.status_code == 200
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match is not None
    reset_token = match.group(1)

    payload = {
        "token": reset_token,
        "new_password": "newpassword456",
        "new_password_confirm": "newpassword456",
    }
    first = client.post("/v1/auth/password-reset/confirm", json=payload)
    assert first.status_code == 200

    second = client.post("/v1/auth/password-reset/confirm", json=payload)
    assert second.status_code == 400


def test_cleanup_expired_tokens_deletes_only_expired_rows(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={
            "email": "cleanup-target@example.com",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "Cleanup",
            "last_name": "Target",
        },
    )
    db = client.session_factory()
    user = db.query(User).filter(User.email == "cleanup-target@example.com").first()

    live_refresh = RefreshToken(
        user_id=user.id, token_hash="live-refresh-hash", expires_at=datetime.now(UTC) + timedelta(days=1)
    )
    expired_refresh = RefreshToken(
        user_id=user.id, token_hash="expired-refresh-hash", expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    live_reset = PasswordResetToken(
        user_id=user.id, token_hash="live-reset-hash", expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    expired_reset = PasswordResetToken(
        user_id=user.id, token_hash="expired-reset-hash", expires_at=datetime.now(UTC) - timedelta(hours=1)
    )
    db.add_all([live_refresh, expired_refresh, live_reset, expired_reset])
    db.commit()

    refresh_deleted, reset_deleted = cleanup_expired_tokens(db)
    assert (refresh_deleted, reset_deleted) == (1, 1)

    remaining_refresh_hashes = {row.token_hash for row in db.query(RefreshToken).all()}
    remaining_reset_hashes = {row.token_hash for row in db.query(PasswordResetToken).all()}
    assert "live-refresh-hash" in remaining_refresh_hashes
    assert "expired-refresh-hash" not in remaining_refresh_hashes
    assert "live-reset-hash" in remaining_reset_hashes
    assert "expired-reset-hash" not in remaining_reset_hashes
    db.close()
