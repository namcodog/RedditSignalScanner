from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.schemas.base import ORMModel


class WxLoginRequest(ORMModel):
    code: str = Field(min_length=1)


class MiniUserPayload(ORMModel):
    id: str
    wx_openid: str
    nickname: str
    avatar_url:Optional[ str] = None
    plan: str


class WxLoginResponse(ORMModel):
    token: str
    user: MiniUserPayload


class WxProfileUpdateRequest(ORMModel):
    nickname:Optional[ str] = Field(default=None, min_length=1, max_length=64)
    avatar_url:Optional[ str] = None


__all__ = [
    "MiniUserPayload",
    "WxLoginRequest",
    "WxLoginResponse",
    "WxProfileUpdateRequest",
]
