from __future__ import annotations

import importlib

import pytest
from sqlalchemy.pool import NullPool, QueuePool


def _reload_session(monkeypatch: pytest.MonkeyPatch) -> object:
    module = importlib.import_module("app.db.session")
    importlib.reload(module)
    return module


@pytest.mark.asyncio
async def test_create_engine_uses_queue_pool_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SQLALCHEMY_DISABLE_POOL", raising=False)
    session_module = _reload_session(monkeypatch)

    assert isinstance(session_module.engine.pool, QueuePool)
    await session_module.engine.dispose()
    importlib.reload(session_module)


@pytest.mark.asyncio
async def test_create_engine_uses_null_pool_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQLALCHEMY_DISABLE_POOL", "1")
    session_module = _reload_session(monkeypatch)

    assert isinstance(session_module.engine.pool, NullPool)
    await session_module.engine.dispose()
    monkeypatch.delenv("SQLALCHEMY_DISABLE_POOL", raising=False)
    importlib.reload(session_module)
