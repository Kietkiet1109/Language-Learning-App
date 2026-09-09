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


class AuthUser(BaseModel):
    """Expose safe user information to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr


class AuthResponse(BaseModel):
    """Return the authenticated user without exposing sensitive data."""

    user: AuthUser
