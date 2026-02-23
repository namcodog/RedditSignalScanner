from __future__ import annotations

from typing import Iterable

from app.services.hotpost.keywords import HotpostLexicon


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _match_terms(text: str, terms: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for term in terms:
        if term and term in text:
            matches.append(term)
    return matches


def detect_rant_signals(text: str, lexicon: HotpostLexicon) -> dict[str, list[str]]:
    return {
        "strong": _match_terms(text, lexicon.rant_signals.get("strong", [])),
        "medium": _match_terms(text, lexicon.rant_signals.get("medium", [])),
        "weak": _match_terms(text, lexicon.rant_signals.get("weak", [])),
    }


def detect_opportunity_signals(text: str, lexicon: HotpostLexicon) -> dict[str, list[str]]:
    return {
        "seeking": _match_terms(text, lexicon.opportunity_signals.get("seeking", [])),
        "unmet_need": _match_terms(text, lexicon.opportunity_signals.get("unmet_need", [])),
        "resonance": _match_terms(text, lexicon.opportunity_signals.get("resonance", [])),
    }


def detect_discovery_signals(text: str, lexicon: HotpostLexicon) -> dict[str, list[str]]:
    return {
        "positive": _match_terms(text, lexicon.discovery_signals.get("positive", [])),
        "hidden_gem": _match_terms(text, lexicon.discovery_signals.get("hidden_gem", [])),
    }


def compute_signal_score(
    signal_groups: dict[str, list[str]],
    *,
    score: int,
    num_comments: int,
) -> float:
    total_signals = sum(len(v) for v in signal_groups.values())
    return float(total_signals * 10 + (score + num_comments * 2) * 0.01)


def classify_intent_label(text: str, lexicon: HotpostLexicon) -> str:
    already_left = _match_terms(text, lexicon.intent_label.get("already_left", []))
    if already_left:
        return "already_left"
    considering = _match_terms(text, lexicon.intent_label.get("considering", []))
    if considering:
        return "considering"
    return "staying_reluctantly"


def classify_pain_category(text: str, lexicon: HotpostLexicon) -> str:
    best_category = None
    best_score = 0
    for category, terms in lexicon.pain_categories.items():
        if category == "other":
            continue
        score = 0
        for term in terms:
            if term and term in text:
                score += text.count(term)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category or "other"


def normalize_pain_category_label(label: str, lexicon: HotpostLexicon) -> str | None:
    normalized = normalize_text(label)
    if not normalized:
        return None
    for category in lexicon.pain_categories.keys():
        if category == "other":
            continue
        if category in normalized:
            return category
    for category, terms in lexicon.pain_categories.items():
        if category == "other":
            continue
        if _match_terms(normalized, terms):
            return category
    zh_map = {
        "定价": "pricing",
        "价格": "pricing",
        "昂贵": "pricing",
        "材料": "quality",
        "做工": "quality",
        "质量": "quality",
        "性能": "performance",
        "卡顿": "performance",
        "慢": "performance",
        "可靠": "reliability",
        "故障": "reliability",
        "坏": "reliability",
        "客服": "support",
        "售后": "support",
        "支持": "support",
        "说明书": "instructions",
        "手册": "instructions",
        "教程": "instructions",
        "物流": "shipping",
        "快递": "shipping",
        "运输": "shipping",
        "兼容": "compatibility",
        "体验": "ux",
        "界面": "ux",
        "交互": "ux",
    }
    for token, category in zh_map.items():
        if token in label:
            return category
    return None


def count_resonance(comments: Iterable[dict[str, str]], lexicon: HotpostLexicon) -> int:
    resonance_terms = lexicon.opportunity_signals.get("resonance", [])
    count = 0
    for comment in comments:
        body = normalize_text(str(comment.get("body", "")))
        if _match_terms(body, resonance_terms):
            count += 1
    return count


__all__ = [
    "normalize_text",
    "detect_rant_signals",
    "detect_opportunity_signals",
    "detect_discovery_signals",
    "compute_signal_score",
    "classify_intent_label",
    "classify_pain_category",
    "normalize_pain_category_label",
    "count_resonance",
]
