from __future__ import annotations

import re

from app.schemas.hotpost_clues import QuotePreview


SIGNAL_SKILL_VARIANTS: dict[str, dict[str, str | bool]] = {
    "baseline_v1": {"label": "baseline", "why_now_mode": "baseline", "clean_quotes": False, "prompt_mode": "baseline"},
    "human_summary_v1": {"label": "human_summary", "why_now_mode": "baseline", "clean_quotes": False, "prompt_mode": "human_summary"},
    "human_summary_tight_why_now_v1": {
        "label": "human_summary",
        "why_now_mode": "tight",
        "clean_quotes": False,
        "prompt_mode": "human_summary",
    },
    "human_summary_tight_why_now_clean_quotes_v2": {
        "label": "human_summary",
        "why_now_mode": "tight",
        "clean_quotes": True,
        "prompt_mode": "human_summary_clean_quotes",
    },
    "judgment_forward_summary_v2": {
        "label": "judgment_forward",
        "why_now_mode": "tight",
        "clean_quotes": True,
        "prompt_mode": "judgment_forward",
    },
    "judgment_forward_summary_strict_v2": {
        "label": "judgment_forward",
        "why_now_mode": "tight",
        "clean_quotes": True,
        "prompt_mode": "judgment_forward_strict",
    },
    "paid_econ_decision_v1": {
        "label": "pack_paid_econ",
        "why_now_mode": "pack_paid_econ",
        "clean_quotes": True,
        "prompt_mode": "paid_econ_decision",
    },
    "paid_econ_decision_strict_v1": {
        "label": "pack_paid_econ",
        "why_now_mode": "pack_paid_econ",
        "clean_quotes": True,
        "prompt_mode": "paid_econ_decision_strict",
    },
    "paid_econ_signal_readout_v2": {
        "label": "pack_paid_econ",
        "why_now_mode": "pack_paid_econ_signal",
        "clean_quotes": True,
        "prompt_mode": "paid_econ_signal_readout",
    },
    "tools_efficiency_focus_v1": {
        "label": "pack_tools_efficiency",
        "why_now_mode": "pack_tools_efficiency",
        "clean_quotes": True,
        "prompt_mode": "tools_efficiency_focus",
    },
    "tools_efficiency_focus_strict_v1": {
        "label": "pack_tools_efficiency",
        "why_now_mode": "pack_tools_efficiency",
        "clean_quotes": True,
        "prompt_mode": "tools_efficiency_focus_strict",
    },
}

LOW_VALUE_QUOTE_NEEDLES = (
    "i am a bot",
    "contact the moderators",
    "hit me up if",
    "automatic",
    "auto moderator",
    "automoderator",
)


def should_clean_quotes(variant_id: str) -> bool:
    return bool(SIGNAL_SKILL_VARIANTS[variant_id]["clean_quotes"])


def clean_experiment_quotes(quotes: list[QuotePreview], *, variant_id: str) -> list[QuotePreview]:
    if not should_clean_quotes(variant_id):
        return quotes
    kept = [quote for quote in quotes if not any(needle in quote.text.lower() for needle in LOW_VALUE_QUOTE_NEEDLES)]
    return kept or quotes


def clean_summary_noise(text: str) -> str:
    cleaned = re.sub(r"\br/[A-Za-z0-9_]+\b[、， ]*", "", text)
    cleaned = re.sub(r"[“\"]?[A-Za-z][A-Za-z0-9 ,.'\":;()/\\\\-]{24,}[”\"]?", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip("，。 ") + ("。" if cleaned and cleaned[-1] not in "。！？" else "")


def time_window_from_reason(why_now_reason: str) -> str:
    if why_now_reason == "new_threads_24h":
        return "24h"
    if why_now_reason in {"switch_signal_7d", "recurring_7d"}:
        return "7d"
    return "30d"


def all_banned_patterns(rules: dict) -> list[str]:
    patterns = rules.get("banned_patterns") or {}
    return [str(item).strip() for item in patterns.get("global", []) if str(item).strip()]


def production_signal_variant(topic_pack_id:Optional[ str], *, rules: dict) ->Optional[ str]:
    raw = rules.get("signal_variants") or {}
    production_by_pack = raw.get("production_by_pack") or {}
    if not isinstance(production_by_pack, dict):
        raise ValueError("card_content_rules.yaml signal_variants.production_by_pack is invalid")
    variant_id = str(production_by_pack.get(topic_pack_id or "") or "").strip()
    return variant_id or None


__all__ = [
    "SIGNAL_SKILL_VARIANTS",
    "all_banned_patterns",
    "clean_experiment_quotes",
    "clean_summary_noise",
    "production_signal_variant",
    "time_window_from_reason",
]
