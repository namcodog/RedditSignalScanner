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


def classify_rant_friction_category(text: str, lexicon: HotpostLexicon) -> str:
    best_category = None
    best_score = 0
    for category, terms in lexicon.rant_friction_categories.items():
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
    for category in lexicon.rant_friction_categories.keys():
        if category == "other":
            continue
        if category in normalized or category.replace("_", " ") in normalized:
            return category
    for category, terms in lexicon.rant_friction_categories.items():
        if category == "other":
            continue
        if _match_terms(normalized, terms):
            return category
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


_VOICE_PAIN_META = {
    "support": {
        "description": "用户抱怨集中在售后、退款或支持流程，问题不是态度一句话，而是事情迟迟解决不了。",
        "implication": "先把售后、退款和支持流程收短，别让用户为同一个问题反复追问。",
    },
    "pricing": {
        "description": "用户不只是嫌贵，而是觉得价格和到手体验不匹配。",
        "implication": "先把价格、套餐和实际能力讲清楚，减少买前期待和买后落差。",
    },
    "reliability": {
        "description": "用户抱怨的是稳定性和可靠性，问题已经影响他们是否敢继续依赖。",
        "implication": "先修最常复现的稳定性问题，并把已知边界讲清楚。",
    },
    "performance": {
        "description": "用户觉得效果和性能没有跟上预期，不是不会用，而是用了仍然不给力。",
        "implication": "先把性能瓶颈和真实效果边界说清楚，再处理最影响结果的场景。",
    },
    "ux": {
        "description": "用户的不满集中在流程绕、上手难、日常操作费劲。",
        "implication": "先简化最常用路径，把新用户最容易卡住的步骤拆掉。",
    },
    "quality": {
        "description": "用户觉得质量和做工撑不起预期，拿到手就开始失望。",
        "implication": "先对齐宣传和实际质量，把最容易引发退货的点讲清楚或改掉。",
    },
    "instructions": {
        "description": "用户卡在说明、教程或引导不清楚，很多步骤都要自己摸索。",
        "implication": "先补清楚安装、上手和失败处理说明，减少买后摸索成本。",
    },
    "shipping": {
        "description": "用户抱怨集中在配送、缺件、退换货等买后环节。",
        "implication": "先把配送、缺件和退换货流程讲清楚，并减少买后等待和沟通成本。",
    },
    "compatibility": {
        "description": "用户买回去才发现兼容性不够，接不进原来的设备或流程。",
        "implication": "先把兼容边界和不适用场景提前讲清楚。",
    },
    "other": {
        "description": "大家抱怨的不是一句抽象空话，而是日常使用里反复出现的小麻烦堆在一起，越用越烦。",
        "implication": "先把用户反复提到的这个具体抱怨收掉，别再让同一种使用挫败持续出现。",
    },
}


def voice_pain_meta(category: str | None) -> dict[str, str] | None:
    normalized = normalize_text(str(category or ""))
    if not normalized:
        return None
    return _VOICE_PAIN_META.get(normalized)


def resolve_rant_semantic_lane(query_family: str | None) -> str:
    normalized = normalize_text(str(query_family or ""))
    if normalized in {"specific_issue", "comparison_complaint_discovery"}:
        return "voice"
    return "business"


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
    "classify_rant_friction_category",
    "normalize_pain_category_label",
    "resolve_rant_semantic_lane",
    "voice_pain_meta",
    "count_resonance",
]
