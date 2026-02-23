"""Hotpost (boom-post) module services."""

from app.services.hotpost.keywords import HotpostLexicon, load_default_hotpost_keywords
from app.services.hotpost.rules import (
    normalize_text,
    detect_rant_signals,
    detect_opportunity_signals,
    detect_discovery_signals,
    compute_signal_score,
    classify_intent_label,
    classify_pain_category,
    count_resonance,
)

__all__ = [
    "HotpostLexicon",
    "load_default_hotpost_keywords",
    "normalize_text",
    "detect_rant_signals",
    "detect_opportunity_signals",
    "detect_discovery_signals",
    "compute_signal_score",
    "classify_intent_label",
    "classify_pain_category",
    "count_resonance",
]
