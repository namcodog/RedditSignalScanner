from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import ORMModel
from app.models.user import MembershipLevel


class RegisterRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    membership_level: MembershipLevel | None = Field(default=None)


class LoginRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthUser(ORMModel):
    id: UUID
    email: EmailStr
    membership_level: MembershipLevel = Field(default=MembershipLevel.FREE)


class AuthTokenResponse(ORMModel):
    access_token: str
    token_type: str = Field(default="bearer")
    expires_at: datetime
    user: AuthUser


__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "AuthTokenResponse",
    "AuthUser",
]
