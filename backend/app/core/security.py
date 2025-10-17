from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ValidationError, field_validator

from app.core.config import Settings, get_settings


class TokenPayload(BaseModel):  # type: ignore[misc]
    sub: str
    exp: Optional[int] = None
    tenant_id: Optional[str] = None
    email: Optional[str] = None

    @field_validator("sub")  # type: ignore[misc]
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


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("utf-8"))


def hash_password(password: str, *, iterations: int = 100_000) -> str:
    if not password:
        raise ValueError("password must not be empty")

    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iteration_str, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iteration_str)
    except ValueError:
        return False

    salt = _b64decode(salt_b64)
    expected = _b64decode(hash_b64)
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(expected, computed)


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
