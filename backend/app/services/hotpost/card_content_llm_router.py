from __future__ import annotations

import os
from typing import Optional, Any

from app.services.llm.clients.gemini_client import GeminiChatClient
from app.services.llm.clients.openai_client import OpenAIChatClient

_GOOGLE_PREFIX = "google/"
_DEEPSEEK_PREFIX = "deepseek/"
_DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"


def build_card_content_client(
    model: str, *, timeout: float
) -> OpenAIChatClient | GeminiChatClient:
    if _is_google_model(model):
        return GeminiChatClient(model=_strip_google_prefix(model), timeout=timeout)
    if _is_deepseek_model(model):
        return OpenAIChatClient(
            model=_strip_deepseek_prefix(model),
            timeout=timeout,
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            base_url=_deepseek_base_url(),
        )
    return OpenAIChatClient(model=model, timeout=timeout)


def normalize_card_content_llm_profiles(raw_profiles: Any) -> dict[str, dict[str, Any]]:
    if raw_profiles is None:
        return {}
    if not isinstance(raw_profiles, dict):
        raise ValueError("hotpost_quality.yaml llm_routing.profiles is invalid")

    profiles: dict[str, dict[str, Any]] = {}
    for raw_profile_id, raw_profile in raw_profiles.items():
        profile_id = str(raw_profile_id or "").strip()
        if not profile_id:
            continue
        if not isinstance(raw_profile, dict):
            raise ValueError(
                f"hotpost_quality.yaml llm_routing.profiles.{profile_id} is invalid"
            )
        semantic_model = str(raw_profile.get("semantic_model") or "").strip()
        writer_model = str(raw_profile.get("writer_model") or "").strip()
        if not semantic_model or not writer_model:
            raise ValueError(
                f"hotpost_quality.yaml llm_routing.profiles.{profile_id} missing semantic_model or writer_model"
            )
        profiles[profile_id] = {
            "semantic_model": semantic_model,
            "writer_model": writer_model,
            "enabled_by_default": bool(raw_profile.get("enabled_by_default", False)),
        }
    return profiles


def resolve_card_content_llm_profile(
    *,
    models: dict[str, Any],
    profile_id: Optional[str],
) -> dict[str, Any] | None:
    normalized_profile_id = str(profile_id or "").strip()
    if not normalized_profile_id:
        return None
    profiles = models.get("route_profiles") or {}
    if not isinstance(profiles, dict):
        raise ValueError("card content route_profiles is invalid")
    profile = profiles.get(normalized_profile_id)
    if not isinstance(profile, dict):
        raise KeyError(f"Unknown card content LLM profile: {normalized_profile_id}")
    return dict(profile)


def resolve_production_card_content_llm_profile(
    *, models: dict[str, Any]
) -> dict[str, Any] | None:
    profile_id = str(models.get("production_profile_id") or "").strip()
    if not profile_id:
        return None
    profile = resolve_card_content_llm_profile(models=models, profile_id=profile_id)
    if profile is None:
        return None
    return {"profile_id": profile_id, **profile}


def resolve_card_content_model_route(
    *,
    models: dict[str, Any],
    topic_pack_id: Optional[str],
    lane: Optional[str],
    default_timeout: float,
) -> tuple[str, float]:
    lane_overrides = models.get("fast_model_lane_overrides") or {}
    raw_lane = lane_overrides.get((lane or "").strip())
    if isinstance(raw_lane, dict):
        lane_model = str(raw_lane.get("model") or "").strip()
        if lane_model:
            lane_timeout = float(raw_lane.get("timeout_seconds") or default_timeout)
            return lane_model, lane_timeout

    overrides = models.get("fast_model_pack_overrides") or {}
    raw = overrides.get(topic_pack_id or "")
    if isinstance(raw, dict):
        model = str(raw.get("model") or "").strip()
        if model:
            timeout = float(raw.get("timeout_seconds") or default_timeout)
            return model, timeout
    return str(models["fast_model"]), default_timeout


def _is_google_model(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized.startswith(_GOOGLE_PREFIX) or normalized.startswith("gemini")


def _is_deepseek_model(model: str) -> bool:
    return model.strip().lower().startswith(_DEEPSEEK_PREFIX)


def _strip_google_prefix(model: str) -> str:
    return model.split("/", 1)[1] if model.startswith(_GOOGLE_PREFIX) else model


def _strip_deepseek_prefix(model: str) -> str:
    return model.split("/", 1)[1] if model.startswith(_DEEPSEEK_PREFIX) else model


def _deepseek_base_url() -> str:
    return (
        (os.getenv("DEEPSEEK_BASE_URL") or _DEEPSEEK_DEFAULT_BASE_URL)
        .strip()
        .rstrip("/")
    )
