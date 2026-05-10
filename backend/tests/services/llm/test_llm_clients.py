from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

from app.services.llm.clients.gemini_client import GeminiChatClient
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.llm.interfaces import LLMClientError


@pytest.mark.asyncio
async def test_openai_client_raises_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OpenAIChatClient(model="gpt-test", api_key="test-key")
    client._sdk = None

    def _raise_http_error(*_args: Any, **_kwargs: Any) -> Any:
        raise urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=503,
            msg="boom",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"temporary down"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", _raise_http_error)

    with pytest.raises(LLMClientError, match="openai"):
        await client.generate("hello")


@pytest.mark.asyncio
async def test_gemini_client_raises_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GeminiChatClient(model="gemini-test", api_key="test-key")

    def _raise_http_error(*_args: Any, **_kwargs: Any) -> Any:
        raise urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
            code=429,
            msg="rate limited",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"rate limited"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", _raise_http_error)

    with pytest.raises(LLMClientError, match="gemini"):
        await client.generate("hello")


@pytest.mark.asyncio
async def test_gemini_client_raises_on_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = GeminiChatClient(model="gemini-test", api_key=None)

    with pytest.raises(LLMClientError, match="missing API key"):
        await client.generate("hello")


@pytest.mark.asyncio
async def test_gemini_client_sends_response_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class _Response:
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}'
            )

    def _capture_request(req: Any, *_args: Any, **_kwargs: Any) -> _Response:
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", _capture_request)
    client = GeminiChatClient(model="gemini-test", api_key="test-key")
    schema = {
        "type": "OBJECT",
        "properties": {"ok": {"type": "BOOLEAN"}},
        "required": ["ok"],
    }

    await client.generate(
        "hello", response_format={"type": "json_object", "schema": schema}
    )

    generation_config = captured["payload"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseJsonSchema"] == schema
