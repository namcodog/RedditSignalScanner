from __future__ import annotations

import json
from typing import Optional, Any


_SECTION_TITLES = [
    "1. 开篇概览",
    "2. 决策风向标",
    "3. 概览（市场健康度诊断）",
    "4. 核心战场推荐（画像分级）",
    "5. 用户痛点拆解",
    "6. 关键决策驱动力",
    "7. 商业机会",
]

_FACT_KEYS = (
    "trend_summary",
    "market_saturation",
    "battlefield_profiles",
    "top_drivers",
    "business_signals",
)


def _compact_value(value: Any, *, depth: int = 0) -> Any:
    if depth >= 2:
        if isinstance(value, list):
            return f"{len(value)} items"
        if isinstance(value, dict):
            return list(value.keys())[:6]
        return value

    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for key in list(value.keys())[:8]:
            compacted[str(key)] = _compact_value(value[key], depth=depth + 1)
        return compacted

    if isinstance(value, list):
        return [_compact_value(item, depth=depth + 1) for item in value[:3]]

    return value


def _trim_evidence_chain(items:Optional[ list[dict[str, Any]]]) -> list[dict[str, str]]:
    if not items:
        return []
    trimmed: list[dict[str, str]] = []
    for item in items[:2]:
        title = str(item.get("title") or "").strip()
        note = str(item.get("note") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title:
            continue
        trimmed.append(
            {
                "title": title,
                "note": note,
                "url": url,
            }
        )
    return trimmed


def build_narrative_report_brief(
    *,
    report_structured: dict[str, Any],
    facts_slice: Any,
) -> str:
    pain_points = report_structured.get("pain_points") or []
    opportunities = report_structured.get("opportunities") or []
    battlefields = report_structured.get("battlefields") or []
    drivers = report_structured.get("drivers") or []
    decision_cards = report_structured.get("decision_cards") or []

    facts_focus: dict[str, Any] = {}
    if isinstance(facts_slice, dict):
        for key in _FACT_KEYS:
            if key in facts_slice:
                facts_focus[key] = _compact_value(facts_slice.get(key))

    brief = {
        "section_contract": _SECTION_TITLES,
        "canonical_titles": {
            "decision_cards": [str(card.get("title") or "").strip() for card in decision_cards if card],
            "battlefields": [str(item.get("name") or "").strip() for item in battlefields if item],
            "pain_points": [str(item.get("title") or "").strip() for item in pain_points if item],
            "drivers": [str(item.get("title") or "").strip() for item in drivers if item],
            "opportunities": [str(item.get("title") or "").strip() for item in opportunities if item],
        },
        "evidence_contract": {
            "pain_points": [
                {
                    "title": str(item.get("title") or "").strip(),
                    "user_voices": (item.get("user_voices") or [])[:2],
                    "evidence_chain": _trim_evidence_chain(item.get("evidence_chain")),
                }
                for item in pain_points[:3]
            ],
            "opportunities": [
                {
                    "title": str(item.get("title") or "").strip(),
                    "target_communities": (item.get("target_communities") or [])[:3],
                    "evidence_chain": _trim_evidence_chain(item.get("evidence_chain")),
                }
                for item in opportunities[:2]
            ],
        },
        "facts_focus": facts_focus,
    }
    return json.dumps(brief, ensure_ascii=False, indent=2)


__all__ = ["build_narrative_report_brief"]
