from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator, model_validator

# Matches the DB column widths in app/models.py (String(32) / String(16) / String(64)).
# Empty string is allowed here — it means "clear this optional field" (see F-004 criterion 7);
# routers/users.py::update_me converts "" to None before it reaches the DB.
PHONE_PATTERN = r"^[0-9+\-\s()]{0,32}$"
LOCALE_PATTERN = r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$"


def _check_bcrypt_byte_length(v: str) -> str:
    # bcrypt (5.x) raises ValueError instead of truncating past 72 bytes — reject here
    # with a clean 422 instead of letting that surface as a 500 (see specs/security/requirements.md).
    if len(v.encode("utf-8")) > 72:
        raise ValueError("must be at most 72 bytes")
    return v


# Any field that reaches hash_password/verify_password/verify_password_timing_safe needs this.
BcryptPassword = Annotated[str, AfterValidator(_check_bcrypt_byte_length)]


def _strip_and_require_nonblank(v: str) -> str:
    # Field(min_length=1) only checks the raw input, so a whitespace-only string
    # (e.g. "   ") passes it and would otherwise be stored blank after stripping
    # (docs/tech-debt.md item 32). Strip here and re-check, after the length
    # constraints have already run, so a genuinely blank name is rejected with 422
    # instead of silently saved.
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


# first_name/last_name on both RegisterRequest and ProfileUpdate need this.
NonBlankName = Annotated[str, AfterValidator(_strip_and_require_nonblank)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: BcryptPassword = Field(min_length=8)
    password_confirm: str = Field(min_length=8)
    first_name: NonBlankName = Field(min_length=1, max_length=100)
    last_name: NonBlankName = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: BcryptPassword


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    locale: str
    timezone: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: NonBlankName | None = Field(default=None, min_length=1, max_length=100)
    last_name: NonBlankName | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=32, pattern=PHONE_PATTERN)
    locale: str | None = Field(default=None, max_length=16, pattern=LOCALE_PATTERN)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in available_timezones():
            raise ValueError("must be a valid IANA time zone name")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: BcryptPassword
    new_password: BcryptPassword = Field(min_length=8)
    new_password_confirm: str = Field(min_length=8)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirm:
            raise ValueError("passwords do not match")
        return self


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: BcryptPassword = Field(min_length=8)
    new_password_confirm: str = Field(min_length=8)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordResetConfirm":
        if self.new_password != self.new_password_confirm:
            raise ValueError("passwords do not match")
        return self


class MessageResponse(BaseModel):
    message: str
    reset_token: str | None = None
