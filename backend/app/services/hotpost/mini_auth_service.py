from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token
from app.models.mini_user import MiniUser
from app.schemas.hotpost_wx_auth import MiniUserPayload, WxLoginResponse


async def login_mini_user(db: AsyncSession, session_data: dict[str, str]) -> MiniUser:
    user = await db.scalar(select(MiniUser).where(MiniUser.wx_openid == session_data["openid"]))
    if user is None:
        user = MiniUser(wx_openid=session_data["openid"], wx_unionid=session_data.get("unionid"))
        db.add(user)
    user.wx_unionid = session_data.get("unionid")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def update_mini_profile(db: AsyncSession, user: MiniUser, nickname:Optional[ str], avatar_url:Optional[ str]) -> MiniUser:
    if nickname is not None:
        user.nickname = nickname.strip()
    if avatar_url is not None:
        user.avatar_url = avatar_url.strip() or None
    await db.commit()
    await db.refresh(user)
    return user


def to_mini_user_payload(user: MiniUser) -> MiniUserPayload:
    return MiniUserPayload(
        id=str(user.id),
        wx_openid=user.wx_openid,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        plan=user.plan,
    )


def build_login_response(user: MiniUser, settings: Settings) -> WxLoginResponse:
    token, _ = create_access_token(user.id, tenant_id="mini", source="mini", settings=settings)
    return WxLoginResponse(token=token, user=to_mini_user_payload(user))


__all__ = ["build_login_response", "login_mini_user", "to_mini_user_payload", "update_mini_profile"]
