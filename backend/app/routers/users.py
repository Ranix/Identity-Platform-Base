from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ChangePasswordRequest, ProfileUpdate, UserPublic
from app.security import (
    hash_password,
    normalize_email,
    revoke_all_refresh_tokens,
    verify_password,
)

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_me(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    data = body.model_dump(exclude_unset=True)
    for required_field in ("first_name", "last_name", "email"):
        if required_field in data and data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{required_field} cannot be null",
            )
    if data.get("phone") == "":
        data["phone"] = None
    if "email" in data and data["email"] is not None:
        data["email"] = normalize_email(data["email"])
        if data["email"] != current_user.email:
            data["email_verified"] = False
    for key, value in data.items():
        setattr(current_user, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use") from exc
    db.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    revoke_all_refresh_tokens(db, current_user)
    db.commit()
