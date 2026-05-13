from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.services.hotpost.wx_session_service import wx_code_to_session


@pytest.mark.asyncio
async def test_wx_code_to_session_reports_missing_secret() -> None:
    with pytest.raises(HTTPException) as exc:
        await wx_code_to_session("dummy-code", "wx7694d11984095629", "")

    assert exc.value.status_code == 503
    assert exc.value.detail == "微信小程序配置缺失: secret"


@pytest.mark.asyncio
async def test_wx_code_to_session_reports_timeout() -> None:
    client = AsyncMock()
    client.get.side_effect = httpx.TimeoutException("timeout")
    client_ctx = AsyncMock()
    client_ctx.__aenter__.return_value = client
    client_ctx.__aexit__.return_value = False

    with patch("app.services.hotpost.wx_session_service.httpx.AsyncClient", return_value=client_ctx):
        with pytest.raises(HTTPException) as exc:
            await wx_code_to_session("dummy-code", "wx-appid", "wx-secret")

    assert exc.value.status_code == 503
    assert exc.value.detail == "微信登录服务超时，请稍后再试"


@pytest.mark.asyncio
async def test_wx_code_to_session_reports_invalid_payload() -> None:
    response = Mock()
    response.json.side_effect = ValueError("bad-json")
    client = AsyncMock()
    client.get.return_value = response
    client_ctx = AsyncMock()
    client_ctx.__aenter__.return_value = client
    client_ctx.__aexit__.return_value = False

    with patch("app.services.hotpost.wx_session_service.httpx.AsyncClient", return_value=client_ctx):
        with pytest.raises(HTTPException) as exc:
            await wx_code_to_session("dummy-code", "wx-appid", "wx-secret")

    assert exc.value.status_code == 502
    assert exc.value.detail == "微信登录返回异常，请稍后再试"
