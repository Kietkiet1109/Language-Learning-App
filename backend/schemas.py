"""Pydantic schemas for authentication requests and responses."""

from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    """Validate the data required to create a user account."""

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Validate the data required to authenticate a user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordResetRequest(BaseModel):
    """Validate an email address requesting a reset code."""

    email: EmailStr


class PasswordResetVerifyRequest(BaseModel):
    """Validate the email and six-digit code entered by the user."""

    email: EmailStr
    code: str = Field(pattern=r"^[0-9]{6}$")


class PasswordResetConfirmRequest(BaseModel):
    """Validate a reset credential and the replacement password."""

    reset_token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetMessage(BaseModel):
    """Return a safe status message for a password-reset request."""

    message: str


class PasswordResetVerifyResponse(BaseModel):
    """Return the one-time credential needed by the reset page."""

    reset_token: str


class AuthUser(BaseModel):
    """Expose safe user information to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr


class AuthResponse(BaseModel):
    """Return the authenticated user without exposing sensitive data."""

    user: AuthUser
