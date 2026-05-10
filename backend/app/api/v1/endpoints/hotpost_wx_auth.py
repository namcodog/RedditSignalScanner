from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.mini_auth import decode_mini_jwt_token
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models.mini_user import MiniUser
from app.schemas.hotpost_wx_auth import MiniUserPayload, WxLoginRequest, WxLoginResponse, WxProfileUpdateRequest
from app.services.hotpost.mini_auth_service import build_login_response, login_mini_user, to_mini_user_payload, update_mini_profile
from app.services.hotpost.wx_session_service import wx_code_to_session


router = APIRouter(prefix="/hotpost/wx-auth", tags=["hotpost-mini"])


async def _require_mini_user(db: AsyncSession, payload: TokenPayload) -> MiniUser:
    user = await db.scalar(select(MiniUser).where(MiniUser.id == uuid.UUID(payload.sub)))
    if user is None:
        raise HTTPException(status_code=401, detail="Mini user not found")
    return user


@router.post("/login", response_model=WxLoginResponse)
async def wx_login(
    payload: WxLoginRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> WxLoginResponse:
    session_data = await wx_code_to_session(payload.code, settings.wx_mini_appid, settings.wx_mini_secret)
    user = await login_mini_user(db, session_data)
    return build_login_response(user, settings)


@router.put("/profile", response_model=MiniUserPayload)
async def wx_update_profile(
    payload: WxProfileUpdateRequest,
    token: TokenPayload = Depends(decode_mini_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> MiniUserPayload:
    user = await _require_mini_user(db, token)
    updated = await update_mini_profile(db, user, payload.nickname, payload.avatar_url)
    return to_mini_user_payload(updated)


__all__ = ["router", "wx_code_to_session"]
