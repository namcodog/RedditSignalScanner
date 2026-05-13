from __future__ import annotations

from app.services.hotpost.card_content_llm_router import (
    build_card_content_client,
    resolve_card_content_llm_profile,
    resolve_card_content_model_route,
    resolve_production_card_content_llm_profile,
)
from app.services.llm.clients.gemini_client import GeminiChatClient
from app.services.llm.clients.openai_client import OpenAIChatClient


def test_build_card_content_client_routes_plain_gemini_to_gemini_client() -> None:
    client = build_card_content_client("gemini-2.5-flash-lite", timeout=12.0)

    assert isinstance(client, GeminiChatClient)
    assert client._model == "gemini-2.5-flash-lite"


def test_build_card_content_client_routes_google_prefixed_model_to_gemini_client() -> (
    None
):
    client = build_card_content_client("google/gemini-2.5-flash-lite", timeout=12.0)

    assert isinstance(client, GeminiChatClient)
    assert client._model == "gemini-2.5-flash-lite"


def test_build_card_content_client_routes_openai_model_to_openai_client() -> None:
    client = build_card_content_client("gpt-5.4-mini", timeout=12.0)

    assert isinstance(client, OpenAIChatClient)


def test_build_card_content_client_routes_deepseek_to_official_api(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    client = build_card_content_client("deepseek/deepseek-v4-pro", timeout=12.0)

    assert isinstance(client, OpenAIChatClient)
    assert client._base == "https://api.deepseek.com"
    assert client._api_key == "deepseek-key"
    assert client._model == "deepseek-v4-pro"


def test_build_card_content_client_does_not_fallback_deepseek_to_openrouter(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    client = build_card_content_client("deepseek/deepseek-v4-pro", timeout=12.0)

    assert isinstance(client, OpenAIChatClient)
    assert client._base == "https://api.deepseek.com"
    assert client._api_key == ""
    assert client._model == "deepseek-v4-pro"


def test_resolve_card_content_llm_profile_reads_v12_route_without_changing_default_route() -> (
    None
):
    models = {
        "fast_model": "deepseek/deepseek-v4-flash",
        "route_profiles": {
            "hotpost_v12": {
                "semantic_model": "deepseek/deepseek-v4-flash",
                "writer_model": "deepseek/deepseek-v4-pro",
                "enabled_by_default": False,
            }
        },
        "fast_model_lane_overrides": {},
        "fast_model_pack_overrides": {},
    }

    default_model, default_timeout = resolve_card_content_model_route(
        models=models,
        topic_pack_id="agent-builder",
        lane="signal",
        default_timeout=18.0,
    )
    profile = resolve_card_content_llm_profile(models=models, profile_id="hotpost_v12")

    assert default_model == "deepseek/deepseek-v4-flash"
    assert default_timeout == 18.0
    assert profile == {
        "semantic_model": "deepseek/deepseek-v4-flash",
        "writer_model": "deepseek/deepseek-v4-pro",
        "enabled_by_default": False,
    }


def test_resolve_card_content_llm_profile_reads_v13_title_route_without_changing_default_route() -> (
    None
):
    models = {
        "fast_model": "deepseek/deepseek-v4-flash",
        "route_profiles": {
            "hotpost_v13_title_standalone": {
                "semantic_model": "google/gemini-3-flash-preview",
                "writer_model": "deepseek/deepseek-v4-pro",
                "enabled_by_default": False,
            }
        },
        "fast_model_lane_overrides": {},
        "fast_model_pack_overrides": {},
    }

    default_model, default_timeout = resolve_card_content_model_route(
        models=models,
        topic_pack_id="agent-builder",
        lane="signal",
        default_timeout=18.0,
    )
    profile = resolve_card_content_llm_profile(
        models=models, profile_id="hotpost_v13_title_standalone"
    )

    assert default_model == "deepseek/deepseek-v4-flash"
    assert default_timeout == 18.0
    assert profile == {
        "semantic_model": "google/gemini-3-flash-preview",
        "writer_model": "deepseek/deepseek-v4-pro",
        "enabled_by_default": False,
    }


def test_resolve_production_card_content_llm_profile_uses_explicit_profile_id() -> None:
    models = {
        "production_profile_id": "hotpost_v13_title_standalone",
        "route_profiles": {
            "hotpost_v13_title_standalone": {
                "semantic_model": "google/gemini-3-flash-preview",
                "writer_model": "deepseek/deepseek-v4-pro",
                "enabled_by_default": False,
            }
        },
    }

    profile = resolve_production_card_content_llm_profile(models=models)

    assert profile == {
        "profile_id": "hotpost_v13_title_standalone",
        "semantic_model": "google/gemini-3-flash-preview",
        "writer_model": "deepseek/deepseek-v4-pro",
        "enabled_by_default": False,
    }
