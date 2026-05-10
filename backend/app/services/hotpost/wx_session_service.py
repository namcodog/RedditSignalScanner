from __future__ import annotations

import httpx
from fastapi import HTTPException, status


async def wx_code_to_session(code: str, appid: str, secret: str) -> dict[str, str]:
    missing = []
    if not appid:
        missing.append("appid")
    if not secret:
        missing.append("secret")
    if missing:
        raise HTTPException(status_code=503, detail=f"微信小程序配置缺失: {', '.join(missing)}")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={"appid": appid, "secret": secret, "js_code": code, "grant_type": "authorization_code"},
            )
        data = resp.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=503, detail="微信登录服务超时，请稍后再试") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="微信登录服务暂时不可用") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="微信登录返回异常，请稍后再试") from exc
    if "openid" not in data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=data.get("errmsg", "微信登录失败"),
        )
    return data


__all__ = ["wx_code_to_session"]
