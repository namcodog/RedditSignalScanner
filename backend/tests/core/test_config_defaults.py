from __future__ import annotations

import importlib
import os

import pytest


@pytest.mark.asyncio
async def test_database_url_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    config_module = importlib.import_module("app.core.config")
    config_module = importlib.reload(config_module)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_USER", "appuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret")
    monkeypatch.setenv("POSTGRES_DB", "rss")
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert os.getenv("POSTGRES_USER") == "appuser"

    assert settings.database_url.startswith("postgresql+psycopg://appuser:s3cret@db.internal:6543/rss")
    config_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_redis_url_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_HOST", "redis.internal")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_CACHE_DB", "9")

    config_module = importlib.import_module("app.core.config")
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.reddit_cache_redis_url == "redis://redis.internal:6380/9"
    config_module.get_settings.cache_clear()
