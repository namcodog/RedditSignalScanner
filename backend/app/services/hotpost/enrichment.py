from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.rules import normalize_pain_category_label


def enrich_rant_payload(
    payload: dict[str, Any],
    *,
    category_counts: Counter[str],
    lexicon: HotpostLexicon,
    fallback_quotes: list[str],
    evidence_count: int,
) -> dict[str, Any]:
    pain_points = payload.get("pain_points") or []
    if not pain_points:
        return payload

    normalized_points: list[dict[str, Any]] = []
    rank = 1
    for item in pain_points:
        if hasattr(item, "model_dump"):
            data = item.model_dump()
        elif isinstance(item, dict):
            data = dict(item)
        else:
            data = {"category": str(item)}

        label = normalize_pain_category_label(str(data.get("category", "")), lexicon)
        if label:
            data["mentions"] = int(category_counts.get(label, data.get("mentions", 0)))
            data["category_en"] = label

        if data.get("rank") is None:
            data["rank"] = rank

        user_voice = data.get("user_voice")
        if not user_voice:
            evidence_posts = data.get("evidence_posts") or []
            for post in evidence_posts:
                if isinstance(post, dict):
                    body_preview = post.get("body_preview") or ""
                    title = post.get("title") or ""
                elif hasattr(post, "model_dump"):
                    payload = post.model_dump()
                    body_preview = payload.get("body_preview") or ""
                    title = payload.get("title") or ""
                else:
                    body_preview = ""
                    title = ""
                if body_preview:
                    data["user_voice"] = body_preview
                    break
                if title:
                    data["user_voice"] = title
                    break
            if not data.get("user_voice"):
                sample_quotes = data.get("sample_quotes") or []
                data["user_voice"] = (
                    sample_quotes[0] if sample_quotes else (fallback_quotes[0] if fallback_quotes else None)
                )

        if not data.get("business_implication"):
            data["business_implication"] = "需进一步验证"

        if data.get("percentage") is None and evidence_count:
            data["percentage"] = round(float(data.get("mentions", 0)) / evidence_count, 4)

        if not data.get("key_takeaway"):
            data["key_takeaway"] = data.get("description") or "用户集中吐槽该问题"

        normalized_points.append(data)
        rank += 1

    payload["pain_points"] = normalized_points
    return payload


def enrich_opportunity_payload(
    payload: dict[str, Any],
    *,
    me_too_count: int,
    opportunity_strength: str | None = None,
) -> dict[str, Any]:
    unmet_needs = payload.get("unmet_needs")
    if not unmet_needs:
        opportunities = payload.get("opportunities") or []
        if opportunities:
            unmet_needs = []
            rank = 1
            for item in opportunities:
                if isinstance(item, dict):
                    summary = item.get("summary") or "需求缺口"
                else:
                    summary = str(item) or "需求缺口"
                unmet_needs.append(
                    {
                        "rank": rank,
                        "need": summary,
                        "demand_signal": "medium",
                        "me_too_count": me_too_count,
                        "current_workarounds": [],
                        "opportunity_insight": summary,
                        "evidence": [],
                    }
                )
                rank += 1
        payload["unmet_needs"] = unmet_needs
    else:
        for need in unmet_needs:
            if isinstance(need, dict):
                need.setdefault("me_too_count", me_too_count)
                need.setdefault("current_workarounds", [])
                # normalize workaround structure
                normalized_workarounds = []
                for item in need.get("current_workarounds", []):
                    if isinstance(item, dict):
                        entry = dict(item)
                        if "name" not in entry and entry.get("solution"):
                            entry["name"] = entry.get("solution")
                        if "satisfaction" not in entry and entry.get("pain"):
                            entry["satisfaction"] = entry.get("pain")
                        normalized_workarounds.append(entry)
                need["current_workarounds"] = normalized_workarounds
                if need.get("rank") is None:
                    need["rank"] = 1
                if not need.get("user_voice"):
                    evidence_posts = need.get("evidence_posts") or []
                    for post in evidence_posts:
                        if isinstance(post, dict):
                            body_preview = post.get("body_preview") or ""
                            title = post.get("title") or ""
                        else:
                            body_preview = ""
                            title = ""
                        if body_preview:
                            need["user_voice"] = body_preview
                            break
                        if title:
                            need["user_voice"] = title
                            break

    market = payload.get("market_opportunity")
    if isinstance(market, dict):
        if opportunity_strength and not market.get("strength"):
            market["strength"] = opportunity_strength
        payload["market_opportunity"] = market

    return payload


__all__ = ["enrich_rant_payload", "enrich_opportunity_payload"]
