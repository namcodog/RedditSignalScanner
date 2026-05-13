from __future__ import annotations

from typing import Optional, Any

from app.services.hotpost.rant_evidence_helpers import CJK_TEXT_RE
from app.services.hotpost.rant_signal_rules import (
    RANT_EFFORT_GAP_TERMS,
    RANT_LOSS_TERMS,
    RANT_PAID_TERMS,
    RANT_TRAFFIC_TERMS,
    RANT_TRUST_BREAK_TERMS,
    RANT_VALUE_GAP_TERMS,
    build_rant_post_relevant,
    build_rant_post_why,
    build_rant_signal_text,
    build_rant_summary,
    build_voice_rant_post_relevant,
    build_voice_rant_post_why,
    contains_any,
    detect_voice_rant_category,
)
from app.services.hotpost.rules import normalize_text, resolve_rant_semantic_lane, voice_pain_meta

RANT_GENERIC_WHY_MARKERS = {
    "不是简单的吐槽",
    "第一手",
    "系统性问题",
    "根本性缺陷",
    "商业风险信号",
    "值得关注",
    "反映出",
    "暴露了",
}


def rewrite_rant_action(point: Any, candidate: str, *, get_payload_value) -> str:
    category = normalize_text(str(get_payload_value(point, "category") or ""))
    combined = normalize_text(f"{category} {candidate}")
    if any(token in combined for token in ("购买意图", "受众定位", "流量质量")):
        return "先别再只看点击率，先确认广告带来的流量是不是想买的人。"
    if any(token in combined for token in ("高互动低转化", "流量质量与购买意图脱节", "落地页", "购买引导")):
        return "先查点击到下单这段漏斗，重点看商品页、落地页和结账有没有断点。"
    if any(token in combined for token in ("转化归因困难", "归因", "像素", "roi", "whatsapp")):
        return "先把 TikTok 能记录到的下单链路补齐，不然现在算不清广告到底有没有带来订单。"
    shortened = candidate
    for splitter in ("，否则", "，避免", "，并", "，或", "；", "。"):
        if splitter in shortened:
            shortened = shortened.split(splitter, 1)[0]
            break
    for source, target in (
        ("优先优化", "先优化"),
        ("需要建立或整合", "先把"),
        ("需要建立或优化", "先把"),
        ("需要建立", "先把"),
        ("需要优化", "先优化"),
        ("需要", "先"),
    ):
        if shortened.startswith(source):
            shortened = f"{target}{shortened[len(source):]}"
            break
    shortened = " ".join(shortened.split())
    if not shortened.startswith(("先", "优先", "先别", "别")):
        shortened = f"先{shortened}"
    if not shortened.endswith("。"):
        shortened += "。"
    return shortened


def should_replace_rant_post_why(current: Any, *, generated:Optional[ str]) -> bool:
    if not generated:
        return False
    text = " ".join(str(current or "").split())
    if not text or len(text) > 56:
        return True
    if any(marker in text for marker in RANT_GENERIC_WHY_MARKERS):
        return True
    if not any(token in text for token in ("成交", "转化", "销售", "买量", "付费", "广告", "投流", "流量", "曝光")):
        return True
    return False


def should_replace_rant_post_relevant(current: Any, *, generated:Optional[ str]) -> bool:
    if not generated:
        return False
    text = " ".join(str(current or "").split())
    if not text:
        return True
    if text.startswith(("直接命中:", "领域命中:", "命中关键词:")):
        return True
    if "社区语境待验证" in text:
        return True
    if not CJK_TEXT_RE.search(text):
        return True
    return False


def build_rant_recommended_actions(
    payload: dict[str, Any],
    *,
    query_family:Optional[ str] = None,
    primary_friction:Optional[ str] = None,
    get_payload_value,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for point in list(payload.get("pain_points") or [])[:3]:
        candidate = " ".join(str(get_payload_value(point, "business_implication") or "").split())
        if not candidate:
            takeaway = " ".join(str(get_payload_value(point, "key_takeaway") or "").split())
            category = " ".join(str(get_payload_value(point, "category") or "").split())
            if takeaway and category:
                candidate = f"先处理「{category}」：{takeaway}"
            elif takeaway:
                candidate = f"先处理这个问题：{takeaway}"
        if not candidate:
            continue
        if not candidate.startswith(("先", "优先", "先别")):
            category = " ".join(str(get_payload_value(point, "category") or "").split())
            candidate = f"先处理「{category}」：{candidate}" if category else f"先处理这个问题：{candidate}"
        candidate = rewrite_rant_action(point, candidate, get_payload_value=get_payload_value)
        key = normalize_text(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        actions.append(candidate)
    if actions:
        return actions[:3]

    summary = normalize_text(str(payload.get("summary") or ""))
    signal_text = build_rant_signal_text(payload, get_payload_value=get_payload_value)
    if resolve_rant_semantic_lane(query_family) != "business":
        category = detect_voice_rant_category(payload, get_payload_value=get_payload_value)
        meta = voice_pain_meta(category) if category else None
        if meta and meta.get("implication"):
            return [str(meta["implication"])]
        return ["先把用户反复提到的这个具体抱怨收掉，别再让同一种使用挫败持续出现。"]
    normalized_family = str(query_family or "").strip().lower()
    normalized_friction = str(primary_friction or "").strip().lower()
    if normalized_family == "generic_complaint_discovery" or normalized_friction == "trust_gap":
        has_concrete_evidence = bool(payload.get("top_posts") or payload.get("top_quotes"))
        if has_concrete_evidence:
            category = detect_voice_rant_category(payload, get_payload_value=get_payload_value)
            meta = voice_pain_meta(category) if category else None
            if meta and meta.get("implication"):
                return [str(meta["implication"])]
        generic_actions: list[str] = []
        if contains_any(signal_text, RANT_TRUST_BREAK_TERMS):
            generic_actions.append("先把宣传、客服承诺和产品实际能力对齐，别再让用户买到手后觉得被误导。")
        if contains_any(signal_text, RANT_VALUE_GAP_TERMS):
            generic_actions.append("先把性能边界和适用人群讲清楚，别再用过高预期把用户带进来。")
        if contains_any(signal_text, RANT_EFFORT_GAP_TERMS):
            generic_actions.append("先把上手门槛讲清楚，补真实使用步骤和失败边界，减少买后挫败。")
        if generic_actions:
            return generic_actions[:3]
        return [
            "先把宣传、客服承诺和产品实际能力对齐，别再让用户买到手后觉得被误导。",
            "先把性能边界和适用人群讲清楚，减少买前期待和买后落差。",
        ]
    if contains_any(summary, RANT_LOSS_TERMS) and contains_any(summary, RANT_TRAFFIC_TERMS):
        return ["先把流量进来后到下单这段漏斗拆开看，别再只盯曝光和点击。"]
    if contains_any(summary, RANT_PAID_TERMS):
        return ["先把自然流量和付费流量拆开看，确认问题到底出在内容还是投流。"]
    if contains_any(summary, {"宣传不符", "信任危机", "不信", "骗局"}):
        return ["先把宣传、客服话术和真实能力对齐，别再让承诺跑在产品实际表现前面。"]
    if contains_any(summary, {"体验落差", "不值", "不符", "不达标"}):
        return ["先把性能边界和适用人群讲清楚，减少把预期抬得过高的包装和承诺。"]
    return []


def sanitize_rant_expression(
    payload: dict[str, Any],
    *,
    keywords: list[str],
    query_family:Optional[ str] = None,
    primary_friction:Optional[ str] = None,
    get_payload_value,
    set_payload_value,
) -> None:
    semantic_lane = resolve_rant_semantic_lane(query_family)
    summary = build_rant_summary(
        payload,
        keywords=keywords,
        query_family=query_family,
        primary_friction=primary_friction,
        get_payload_value=get_payload_value,
    )
    if summary:
        payload["summary"] = summary
    post_groups: list[list[Any]] = [list(payload.get("top_posts") or []), list(payload.get("top_rants") or [])]
    for point in payload.get("pain_points") or []:
        if isinstance(point, dict):
            post_groups.append(list(point.get("evidence_posts") or []))
    for posts in post_groups:
        for post in posts:
            if semantic_lane == "business":
                relevant = build_rant_post_relevant(post, get_payload_value=get_payload_value)
                if should_replace_rant_post_relevant(get_payload_value(post, "why_relevant"), generated=relevant):
                    set_payload_value(post, "why_relevant", relevant)
                generated = build_rant_post_why(post, get_payload_value=get_payload_value)
                if generated:
                    set_payload_value(post, "why_important", generated)
                    continue
                if should_replace_rant_post_why(get_payload_value(post, "why_important"), generated=generated):
                    set_payload_value(post, "why_important", generated)
                continue
            relevant = build_voice_rant_post_relevant(post, get_payload_value=get_payload_value)
            if should_replace_rant_post_relevant(get_payload_value(post, "why_relevant"), generated=relevant):
                set_payload_value(post, "why_relevant", relevant)
            generated = build_voice_rant_post_why(post, get_payload_value=get_payload_value)
            if generated and should_replace_rant_post_why(get_payload_value(post, "why_important"), generated=generated):
                set_payload_value(post, "why_important", generated)
