from __future__ import annotations

import importlib

import pytest


@pytest.mark.asyncio
async def test_get_settings_prefers_openrouter_when_openai_key_is_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-real-key")

    config_module = importlib.import_module("app.core.config")
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.openai_api_key == "sk-or-v1-real-key"
    config_module.get_settings.cache_clear()
