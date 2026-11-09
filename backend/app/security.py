import hashlib
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PasswordResetToken, RefreshToken, User

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# Precomputed once at import time so a login with an unknown email still pays
# the full bcrypt cost — otherwise response timing leaks account existence
# even though the error message stays generic (docs/tech-debt.md item 3).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"no-account-for-this-email", bcrypt.gensalt()).decode("utf-8")


def verify_password_timing_safe(plain: str, hashed: str | None) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), (hashed or _DUMMY_PASSWORD_HASH).encode("utf-8"))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: str) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    expire = now + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if sub is None:
            return None
        return str(sub)
    except JWTError:
        return None


def issue_refresh_token(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    token_hash = hash_token(raw)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    row = RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(row)
    db.commit()
    return raw


def validate_refresh_token(db: Session, raw: str) -> User | None:
    token_hash = hash_token(raw)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(row)
        db.commit()
        return None
    return row.user


def revoke_refresh_token(db: Session, raw: str) -> bool:
    token_hash = hash_token(raw)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def revoke_all_refresh_tokens(db: Session, user: User) -> None:
    """Delete every refresh token for the user. Caller commits (see ADR-0003 addendum)."""
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete(synchronize_session=False)


def create_password_reset(db: Session, user: User) -> str:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    raw = secrets.token_urlsafe(32)
    token_hash = hash_token(raw)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_expire_minutes)
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return raw


# Roughly matches create_password_reset's delete+insert+commit wall-clock cost, so
# password-reset/request's response timing doesn't leak whether the email is
# registered — same anti-enumeration goal as verify_password_timing_safe's dummy
# hash for login, just via a fixed delay instead of equivalent DB work, since a
# reset-token row can't be inserted without a real user_id foreign key
# (docs/tech-debt.md item 30).
_DUMMY_RESET_DELAY_SECONDS = 0.05


def simulate_password_reset_work() -> None:
    time.sleep(_DUMMY_RESET_DELAY_SECONDS)


def consume_password_reset(db: Session, raw: str) -> User | None:
    """Mark the token used. Does not commit — caller commits together with the password update."""
    token_hash = hash_token(raw)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None))
        .first()
    )
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return None
    row.used_at = datetime.now(UTC)
    return row.user


def cleanup_expired_tokens(db: Session) -> tuple[int, int]:
    """Delete expired refresh and password-reset tokens. Returns (refresh_deleted, reset_deleted).

    Compares in Python rather than filtering by `expires_at` in SQL: SQLite (tests) stores
    naive datetimes while Postgres (runtime) stores timezone-aware ones, so a SQL-level
    comparison against an aware `now` would behave inconsistently across the two (see the
    CLAUDE.md gotcha the per-row guards elsewhere in this file also work around).
    """
    now = datetime.now(UTC)

    def _is_expired(expires_at: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at < now

    expired_refresh = [row for row in db.query(RefreshToken).all() if _is_expired(row.expires_at)]
    expired_resets = [row for row in db.query(PasswordResetToken).all() if _is_expired(row.expires_at)]

    for row in expired_refresh:
        db.delete(row)
    for row in expired_resets:
        db.delete(row)
    db.commit()

    return len(expired_refresh), len(expired_resets)


def log_reset_delivery(raw_token: str) -> None:
    if settings.environment != "local":
        return
    url = f"{settings.public_app_url.rstrip('/')}/reset-password?token={raw_token}"
    logger.warning("password_reset_dev_delivery url=%s", url)
