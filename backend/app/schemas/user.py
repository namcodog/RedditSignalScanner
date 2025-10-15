from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import ORMModel, TimestampedModel


class UserCreate(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class UserRead(TimestampedModel):
    id: UUID
    email: EmailStr
    is_active: bool
