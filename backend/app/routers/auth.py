from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from app.security import (
    consume_password_reset,
    create_access_token,
    create_password_reset,
    hash_password,
    issue_refresh_token,
    log_reset_delivery,
    normalize_email,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    simulate_password_reset_work,
    validate_refresh_token,
    verify_password_timing_safe,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

RESET_MESSAGE = "If an account exists for this email, reset instructions have been sent."


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> User:
    email = normalize_email(body.email)
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = normalize_email(body.email)
    user = db.query(User).filter(User.email == email).first()
    password_ok = verify_password_timing_safe(body.password, user.password_hash if user else None)
    if user is None or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    access, expires_in = create_access_token(str(user.id))
    refresh = issue_refresh_token(db, user)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)) -> None:
    if not revoke_refresh_token(db, body.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = validate_refresh_token(db, body.refresh_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    access, expires_in = create_access_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=body.refresh_token,
        expires_in=expires_in,
    )


@router.post("/password-reset/request", response_model=MessageResponse)
def password_reset_request(body: PasswordResetRequest, db: Session = Depends(get_db)) -> MessageResponse:
    email = normalize_email(body.email)
    user = db.query(User).filter(User.email == email).first()
    reset_token = None
    if user is not None:
        raw = create_password_reset(db, user)
        log_reset_delivery(raw)
        if settings.environment == "local" and settings.dev_expose_reset_token:
            reset_token = raw
    else:
        simulate_password_reset_work()
    return MessageResponse(message=RESET_MESSAGE, reset_token=reset_token)


@router.post("/password-reset/confirm", response_model=MessageResponse)
def password_reset_confirm(body: PasswordResetConfirm, db: Session = Depends(get_db)) -> MessageResponse:
    user = consume_password_reset(db, body.token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user.password_hash = hash_password(body.new_password)
    revoke_all_refresh_tokens(db, user)
    db.commit()
    return MessageResponse(message="Password has been reset.")
