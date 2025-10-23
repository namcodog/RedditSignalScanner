from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    decode_jwt_token,
    TokenPayload,
)
from app.db.session import get_session
from app.models.user import MembershipLevel, User
from app.schemas.auth import AuthTokenResponse, AuthUser, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _issue_token(user: User, settings: Settings) -> AuthTokenResponse:
    token, expires_at = create_access_token(
        user.id, email=user.email, settings=settings
    )
    return AuthTokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=AuthUser(
            id=user.id,
            email=user.email,
            membership_level=user.membership_level,
        ),
    )


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account and receive an access token",
)
async def register_user(
    request: RegisterRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> AuthTokenResponse:
    email = _normalise_email(request.email)

    existing = await _get_user_by_email(db, email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    password_hash = hash_password(request.password)

    membership = MembershipLevel.ensure(request.membership_level)
    user = User(
        email=email,
        password_hash=password_hash,
        membership_level=membership,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    await db.refresh(user)
    return _issue_token(user, settings)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Authenticate existing user and receive an access token",
)
async def login_user(
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> AuthTokenResponse:
    email = _normalise_email(request.email)
    user = await _get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return _issue_token(user, settings)


@router.get(
    "/me",
    response_model=AuthUser,
    summary="Get current authenticated user",
)
async def get_current_user_me(
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> AuthUser:
    # Prefer email from JWT to avoid extra UUID parsing; tokens issued by this app include email
    if payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(id=user.id, email=user.email, membership_level=user.membership_level)


__all__ = ["router"]
