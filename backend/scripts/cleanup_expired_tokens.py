#!/usr/bin/env python
"""Delete expired refresh and password-reset tokens.

Run manually, or schedule externally (cron, host timer) — see README.
No in-process scheduler exists yet; that's Wave 3 (docs/tech-debt.md item 11).
"""

from app.database import SessionLocal
from app.security import cleanup_expired_tokens


def main() -> None:
    db = SessionLocal()
    try:
        refresh_deleted, reset_deleted = cleanup_expired_tokens(db)
        print(
            f"Deleted {refresh_deleted} expired refresh token(s), "
            f"{reset_deleted} expired password reset token(s)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
