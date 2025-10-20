from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.hash import django_pbkdf2_sha256
from pydantic import BaseModel, ValidationError, field_validator

from app.core.config import Settings, get_settings


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[int] = None
    tenant_id: Optional[str] = None
    email: Optional[str] = None

    @field_validator("sub")
    @classmethod
    def validate_sub(cls, value: str) -> str:
        if not value:
            raise ValueError("subject must not be empty")
        return value


http_bearer = HTTPBearer(auto_error=False)


def decode_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        data: TokenPayload = TokenPayload.model_validate(payload)
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if data.exp is not None:
        expires_at = datetime.fromtimestamp(data.exp, tz=timezone.utc)
        if expires_at < datetime.now(tz=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return data


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    # Use Django's PBKDF2-SHA256 format (matches tests), no 72-byte limit
    return django_pbkdf2_sha256.hash(password)


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    try:
        return django_pbkdf2_sha256.verify(password, stored)
    except ValueError:
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    *,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    tenant_id: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Tuple[str, datetime]:
    cfg = settings or get_settings()
    expires = expires_delta or timedelta(hours=24)
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + expires

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": cfg.app_name,
    }
    if email:
        payload["email"] = email
    if tenant_id:
        payload["tenant_id"] = tenant_id

    token = jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
    return token, expires_at


__all__ = [
    "TokenPayload",
    "decode_jwt_token",
    "hash_password",
    "verify_password",
    "create_access_token",
]
