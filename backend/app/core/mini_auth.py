from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.security import TokenPayload, decode_jwt_token


async def decode_mini_jwt_token(
    payload: TokenPayload = Depends(decode_jwt_token),
) -> TokenPayload:
    if payload.source != "mini":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mini token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


__all__ = ["decode_mini_jwt_token"]
