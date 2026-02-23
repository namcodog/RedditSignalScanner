from __future__ import annotations

from app.services.llm.clients.openai_client import resolve_llm_api_key


def test_resolve_llm_api_key_prefers_openrouter_on_openrouter_base(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-openrouter")
    assert resolve_llm_api_key() == "or-openrouter"


def test_resolve_llm_api_key_falls_back_to_openai(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert resolve_llm_api_key() == "sk-openai"
