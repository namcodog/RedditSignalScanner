from __future__ import annotations

from types import SimpleNamespace

from app.services.llm.clients.openai_client import OpenAIChatClient, resolve_llm_api_key


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


def test_resolve_llm_api_key_respects_explicit_empty_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-openrouter")

    assert resolve_llm_api_key(explicit_key="") == ""


def test_openai_sdk_request_receives_configured_timeout(monkeypatch) -> None:
    from app.services.llm.clients import openai_client as mod

    captured: dict[str, dict] = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["create_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(mod, "OpenAI", FakeOpenAI)

    client = OpenAIChatClient(
        "deepseek/deepseek-v4-pro",
        timeout=12.0,
        api_key="test-key",
        base_url="https://api.deepseek.com",
    )

    result = client._chat_completion(
        [{"role": "user", "content": "hi"}],
        max_tokens=8,
        temperature=0.0,
    )

    assert result == "ok"
    assert captured["client_kwargs"]["timeout"] == 12.0
    assert captured["create_kwargs"]["timeout"] == 12.0
