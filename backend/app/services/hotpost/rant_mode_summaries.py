from __future__ import annotations

from typing import Optional, Any

from app.schemas.hotpost import ComplaintFacet
from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.quote_projection import normalize_quote_text
from app.services.hotpost.rules import normalize_text


def build_quote_only_rant_summary(
    complaint_facets: list[ComplaintFacet],
    *,
    payload:Optional[ dict[str, Any]] = None,
    get_payload_value,
) -> str:
    if complaint_facets:
        quote = normalize_quote_text(complaint_facets[0].representative_quote, max_chars=96)
        if quote:
            return f"先看原话，这批讨论里最扎眼的一句是：{quote}"
    if isinstance(payload, dict):
        top_quotes = list(payload.get("top_quotes") or [])
        if top_quotes:
            quote = normalize_quote_text(get_payload_value(top_quotes[0], "quote"), max_chars=96)
            if quote:
                return f"先看原话，这批讨论里最扎眼的一句是：{quote}"
    return "这次先不给你硬凑结论。当前抓到的可用讨论还不够，先把边界说清楚。"


def build_compare_insufficient_summary(*, payload:Optional[ dict[str, Any]] = None, get_payload_value) -> str:
    if isinstance(payload, dict):
        top_quotes = list(payload.get("top_quotes") or [])
        if top_quotes:
            quote = normalize_quote_text(get_payload_value(top_quotes[0], "quote"), max_chars=88)
            if quote:
                return f"先给你看已经找到的原话：{quote}。但目前只够说明有人这么说，还不够支撑稳定的双边比较结论。"
    return "已经找到少量相关原话，但目前还不够支撑稳定的双边比较结论。"


def build_compare_no_hit_summary() -> str:
    return "这次已经翻到相关讨论，但没找到足够明确、能站得住的双边原话，所以先不给你硬凑比较结论。"


def build_compare_rant_summary(
    complaint_facets: list[ComplaintFacet],
    *,
    query: str,
    keywords: list[str],
    payload:Optional[ dict[str, Any]] = None,
    get_payload_value,
) ->Optional[ str]:
    targets = infer_compare_targets(query, keywords)
    if len(targets) < 2:
        return None
    left_quote:Optional[ str] = None
    right_quote:Optional[ str] = None
    for facet in complaint_facets:
        quote = normalize_quote_text(facet.representative_quote, max_chars=72)
        if not quote or not facet.target:
            continue
        if normalize_text(facet.target) == normalize_text(targets[0]) and not left_quote:
            left_quote = quote
        if normalize_text(facet.target) == normalize_text(targets[1]) and not right_quote:
            right_quote = quote
    if (not left_quote or not right_quote) and isinstance(payload, dict):
        for entry in list(payload.get("top_quotes") or []):
            quote = normalize_quote_text(get_payload_value(entry, "quote"), max_chars=72)
            if not quote:
                continue
            normalized_quote = normalize_text(quote)
            if not left_quote and normalize_text(targets[0]) in normalized_quote:
                left_quote = quote
            if not right_quote and normalize_text(targets[1]) in normalized_quote:
                right_quote = quote
            if left_quote and right_quote:
                break
    if not left_quote or not right_quote:
        return None
    return f"偏向{targets[0]}的人常提到“{left_quote}”；嫌弃{targets[1]}的人常提到“{right_quote}”。"


def build_grounded_rant_summary(complaint_facets: list[ComplaintFacet]) ->Optional[ str]:
    # 这层只允许说 evidence 已经长出来的具体骂点，不准回退成泛泛空话。
    if not complaint_facets:
        return None
    first = complaint_facets[0]
    second = complaint_facets[1] if len(complaint_facets) > 1 else None
    if second and second.label != first.label:
        return f"大家骂得最具体的不是泛泛不好用，而是“{first.label}”；其次是“{second.label}”。"
    quote = normalize_quote_text(first.representative_quote, max_chars=88)
    if quote:
        return f"大家最集中的抱怨落在这句原话上：{quote}"
    return None
