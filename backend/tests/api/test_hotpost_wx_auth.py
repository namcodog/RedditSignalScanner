from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.mini_user import MiniUser, MiniUserFavorite


@pytest.mark.asyncio
async def test_wx_login_creates_mini_user(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1.endpoints import hotpost_wx_auth

    async def _mock_wx_session(*_args, **_kwargs) -> dict[str, str]:
        return {"openid": f"wx-openid-{uuid.uuid4().hex}", "unionid": "wx-union-1"}

    monkeypatch.setattr(hotpost_wx_auth, "wx_code_to_session", _mock_wx_session)
    resp = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-1"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["user"]["nickname"] == "探索者"
    assert data["user"]["plan"] == "free"

    stored = await db_session.scalar(
        select(MiniUser).where(MiniUser.wx_openid == data["user"]["wx_openid"])
    )
    assert stored is not None


@pytest.mark.asyncio
async def test_wx_login_reuses_existing_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1.endpoints import hotpost_wx_auth

    openid = f"wx-openid-{uuid.uuid4().hex}"

    async def _mock_wx_session(*_args, **_kwargs) -> dict[str, str]:
        return {"openid": openid, "unionid": "wx-union-1"}

    monkeypatch.setattr(hotpost_wx_auth, "wx_code_to_session", _mock_wx_session)
    first = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-1"})
    second = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-2"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


@pytest.mark.asyncio
async def test_wx_favorites_require_mini_token(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/wx-favorites")
    assert resp.status_code == 401

    token, _ = create_access_token(
        uuid.uuid4(), email="main@example.com", settings=get_settings()
    )
    reject = await client.get(
        "/api/hotpost/wx-favorites", headers={"Authorization": f"Bearer {token}"}
    )
    assert reject.status_code == 401


@pytest.mark.asyncio
async def test_wx_favorites_add_list_delete(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1.endpoints import hotpost_wx_auth

    async def _mock_wx_session(*_args, **_kwargs) -> dict[str, str]:
        return {"openid": f"wx-openid-{uuid.uuid4().hex}", "unionid": "wx-union-1"}

    monkeypatch.setattr(hotpost_wx_auth, "wx_code_to_session", _mock_wx_session)
    login = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-1"})
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    card_id = (await client.get("/api/hotpost/cards")).json()["items"][0]["card_id"]

    created = await client.post(f"/api/hotpost/wx-favorites/{card_id}", headers=headers)
    assert created.status_code == 200

    listed = await client.get("/api/hotpost/wx-favorites", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["card_id"] == card_id
    assert listed.json()["items"][0]["favorited_at"]

    deleted = await client.delete(f"/api/hotpost/wx-favorites/{card_id}", headers=headers)
    assert deleted.status_code == 200
    assert (await client.get("/api/hotpost/wx-favorites", headers=headers)).json()["items"] == []


@pytest.mark.asyncio
async def test_wx_profile_update(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1.endpoints import hotpost_wx_auth

    async def _mock_wx_session(*_args, **_kwargs) -> dict[str, str]:
        return {"openid": f"wx-openid-{uuid.uuid4().hex}", "unionid": "wx-union-1"}

    monkeypatch.setattr(hotpost_wx_auth, "wx_code_to_session", _mock_wx_session)
    login = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-1"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    updated = await client.put(
        "/api/hotpost/wx-auth/profile",
        headers=headers,
        json={"nickname": "新昵称", "avatar_url": "https://example.com/avatar.png"},
    )

    assert updated.status_code == 200
    assert updated.json()["nickname"] == "新昵称"
    assert updated.json()["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_wx_favorites_batch_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.endpoints import hotpost_wx_auth

    async def _mock_wx_session(*_args, **_kwargs) -> dict[str, str]:
        return {"openid": f"wx-openid-{uuid.uuid4().hex}", "unionid": "wx-union-1"}

    monkeypatch.setattr(hotpost_wx_auth, "wx_code_to_session", _mock_wx_session)
    login = await client.post("/api/hotpost/wx-auth/login", json={"code": "code-1"})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    cards = (await client.get("/api/hotpost/cards", params={"page_size": 2})).json()["items"]
    payload = {"card_ids": [cards[0]["card_id"], cards[0]["card_id"], "missing-card", cards[1]["card_id"]]}

    first = await client.post("/api/hotpost/wx-favorites/batch", headers=headers, json=payload)
    second = await client.post("/api/hotpost/wx-favorites/batch", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    favorites = await db_session.scalars(select(MiniUserFavorite))
    assert len(list(favorites)) == 2
