from __future__ import annotations

from typing import Optional, Any, Callable

from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.hotpost.rant_evidence_helpers import contains_term
from app.services.hotpost.rules import (
    classify_pain_category,
    normalize_pain_category_label,
    normalize_text,
    resolve_rant_semantic_lane,
    voice_pain_meta,
)

RANT_TRAFFIC_TERMS = {"traffic", "view", "views", "impression", "impressions", "曝光", "流量"}
RANT_LOSS_TERMS = {"conversion", "conversions", "convert", "sales", "sale", "purchase", "purchases", "成交", "转化", "出单", "购买", "卖不动"}
RANT_PAID_TERMS = {"ads", "ad", "advertising", "paid", "pay to play", "gmv max", "投流", "广告", "买量"}
RANT_RESTRICTION_TERMS = {
    "restricted", "restriction", "restricted items", "authorized dealer", "authorized dealers",
    "policy", "policies", "compliance", "violate", "violating", "sanctioned", "unauthorized",
}
RANT_BRAND_MISMATCH_TERMS = {
    "branding", "representation", "represented", "audience", "demographic", "gap in the market",
    "older", "50 year old", "50 year olds", "over 50", "disability",
}
RANT_INSTABILITY_TERMS = {"random", "randomly", "unstable", "inconsistent", "unpredictable", "随机", "不稳定", "不可预测"}
RANT_TRUST_BREAK_TERMS = {
    "scam", "misleading", "lied", "lying", "false advertising",
    "not as advertised", "support told me", "they told me", "does not have", "doesn't have",
}
RANT_VALUE_GAP_TERMS = {
    "underwhelming", "disappointed", "expected more", "waste of money", "overhyped",
    "doesn't feel strong", "doesnt feel strong", "too weak", "not good enough", "doesn't live up", "doesnt live up",
}
RANT_EFFORT_GAP_TERMS = {"what am i doing wrong", "dial in", "grind finer", "hard to use", "complicated", "learning curve", "fiddly"}
RANT_SUBJECT_LABELS = {
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "youtube": "YouTube",
    "shopify": "Shopify",
    "amazon": "Amazon",
    "etsy": "Etsy",
}

DEFAULT_LEXICON = load_default_hotpost_keywords()


def contains_any(text: str, terms: set[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def _default_get_payload_value(item: Any, field: str) -> Any:
    # 规则模块默认兼容 dict / Pydantic / dataclass，避免 orchestration 细节泄漏进来。
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def primary_rant_subject(keywords: list[str]) ->Optional[ str]:
    for keyword in keywords:
        subject = RANT_SUBJECT_LABELS.get(str(keyword).strip().lower())
        if subject:
            return subject
    return None


def build_rant_signal_text(
    payload: dict[str, Any],
    *,
    get_payload_value:Optional[ Callable[[Any, str], Any]] = None,
) -> str:
    accessor = get_payload_value or _default_get_payload_value
    parts = [str(payload.get("summary") or "")]
    for point in list(payload.get("pain_points") or [])[:1]:
        if isinstance(point, dict):
            for key in ("key_takeaway", "user_voice", "description", "category"):
                parts.append(str(point.get(key) or ""))
    for post in list(payload.get("top_posts") or [])[:1]:
        parts.append(str(accessor(post, "title") or ""))
        parts.append(str(accessor(post, "body_preview") or ""))
    for quote in list(payload.get("top_quotes") or [])[:1]:
        if isinstance(quote, dict):
            parts.append(str(quote.get("quote") or ""))
    return normalize_text(" ".join(part for part in parts if part))


def detect_voice_rant_category(
    payload: dict[str, Any],
    *,
    get_payload_value:Optional[ Callable[[Any, str], Any]] = None,
) ->Optional[ str]:
    del get_payload_value
    for point in list(payload.get("pain_points") or [])[:2]:
        if not isinstance(point, dict):
            continue
        direct_label = str(point.get("category_en") or "").strip().lower()
        if voice_pain_meta(direct_label):
            return direct_label
        for key in ("category", "description", "key_takeaway", "user_voice"):
            label = normalize_pain_category_label(str(point.get(key) or ""), DEFAULT_LEXICON)
            if label and voice_pain_meta(label):
                return label
    detected = classify_pain_category(build_rant_signal_text(payload, get_payload_value=lambda *_: None), DEFAULT_LEXICON)
    return None if detected == "other" else detected


def build_voice_rant_summary(
    payload: dict[str, Any],
    *,
    keywords: list[str],
    query_family:Optional[ str] = None,
) -> str:
    del keywords
    normalized_family = normalize_text(str(query_family or ""))
    thin_sample_quote_mode = normalized_family in {"specific_issue", "comparison_complaint_discovery"}
    evidence_count = int(payload.get("evidence_count") or len(list(payload.get("top_posts") or [])))
    if evidence_count <= 0:
        return "这个问题当前没抓到足够可用讨论，先不硬下结论。"

    quote_text = ""
    for quote in list(payload.get("top_quotes") or []):
        if not isinstance(quote, dict):
            continue
        normalized = " ".join(str(quote.get("quote") or "").split())
        if normalized:
            quote_text = normalized
            break
    if not quote_text:
        for point in list(payload.get("pain_points") or []):
            if not isinstance(point, dict):
                continue
            normalized = " ".join(str(point.get("user_voice") or "").split())
            if normalized:
                quote_text = normalized
                break
            sample_quotes = point.get("sample_quotes")
            if isinstance(sample_quotes, list):
                for sample in sample_quotes:
                    normalized = " ".join(str(sample or "").split())
                    if normalized:
                        quote_text = normalized
                        break
            if quote_text:
                break
    if thin_sample_quote_mode and evidence_count <= 1 and quote_text:
        clipped = f"{quote_text[:90]}…" if len(quote_text) > 90 else quote_text
        return f"目前只抓到少量讨论，代表性抱怨是：{clipped}"

    category = detect_voice_rant_category(payload, get_payload_value=lambda *_: None)
    meta = voice_pain_meta(category) if category else None
    if meta:
        return str(meta.get("description") or "").strip() or "大家抱怨的不是一句抽象空话，而是日常使用里反复出现的小麻烦堆在一起，越用越烦。"
    return "大家抱怨的不是一句抽象空话，而是日常使用里反复出现的小麻烦堆在一起，越用越烦。"


def build_voice_rant_post_why(post: Any, *, get_payload_value) ->Optional[ str]:
    accessor = get_payload_value or _default_get_payload_value
    text = normalize_text(" ".join([str(accessor(post, "title") or ""), str(accessor(post, "body_preview") or "")]))
    if not text:
        return None
    category = classify_pain_category(text, DEFAULT_LEXICON)
    mapping = {
        "support": "这条帖子不是在抱怨态度差而已，而是在说售后、退款或维修流程很长，问题最后还没真正解决。",
        "pricing": "这条帖子不是单纯嫌贵，而是在说收费方式和到手体验不匹配，让人觉得这钱花得不值。",
        "reliability": "这条帖子在说东西不稳定、容易坏，抱怨点已经从一次故障变成不敢继续依赖。",
        "performance": "这条帖子在说效果和性能没跟上预期，用户不是不会用，而是用了还是觉得不给力。",
        "ux": "这条帖子在说流程太绕、太难用，用户的不满集中在上手和日常操作都很费劲。",
        "quality": "这条帖子在说做工和质量感撑不起价格，拿到手就开始掉预期。",
        "instructions": "这条帖子在说说明和引导不清楚，很多步骤都要自己摸索。",
        "shipping": "这条帖子在说配送、缺件或退换货麻烦，问题不是买前而是买后一直发生。",
        "compatibility": "这条帖子在说兼容性差，买回来后才发现接不进原来的设备或流程。",
    }
    if category in mapping:
        return mapping[category]
    if int(accessor(post, "num_comments") or 0) >= 5:
        return "这不是一次性吐槽，评论里也有人继续接同样的问题。"
    return None


def build_voice_rant_post_relevant(post: Any, *, get_payload_value) ->Optional[ str]:
    accessor = get_payload_value or _default_get_payload_value
    text = normalize_text(" ".join([str(accessor(post, "title") or ""), str(accessor(post, "body_preview") or "")]))
    if not text:
        return None
    category = classify_pain_category(text, DEFAULT_LEXICON)
    meta = voice_pain_meta(category) or voice_pain_meta("other") or {}
    return str(meta.get("description") or "").strip() or None


def build_rant_summary(
    payload: dict[str, Any],
    *,
    keywords: list[str],
    query_family:Optional[ str] = None,
    primary_friction:Optional[ str] = None,
    get_payload_value:Optional[ Callable[[Any, str], Any]] = None,
) ->Optional[ str]:
    accessor = get_payload_value or _default_get_payload_value
    text = build_rant_signal_text(payload, get_payload_value=accessor)
    if not text:
        return None
    if resolve_rant_semantic_lane(query_family) != "business":
        return build_voice_rant_summary(payload, keywords=keywords, query_family=query_family)

    subject = primary_rant_subject(keywords)
    normalized_family = str(query_family or "").strip().lower()
    normalized_friction = str(primary_friction or "").strip().lower()
    if normalized_family == "generic_complaint_discovery" or normalized_friction == "trust_gap":
        has_concrete_evidence = bool(payload.get("top_posts") or payload.get("top_quotes"))
        if has_concrete_evidence:
            category = detect_voice_rant_category(payload, get_payload_value=accessor)
            meta = voice_pain_meta(category) if category else None
            if meta and meta.get("description"):
                return str(meta["description"])
        if contains_any(text, RANT_TRUST_BREAK_TERMS):
            return "大家最不满的不是某个小故障，而是宣传、客服承诺和到手体验经常对不上。"
        if contains_any(text, RANT_VALUE_GAP_TERMS):
            return "大家最常抱怨的是买前期待被抬得太高，但到手体验没有值回这个预期。"
        if contains_any(text, RANT_EFFORT_GAP_TERMS):
            return "大家最常抱怨的不是不会用，而是上手和调试比想象中更折腾。"
        return "大家最常抱怨的不是一个点坏了，而是宣传、体验和实际表现经常对不上。"
    if contains_any(text, RANT_INSTABILITY_TERMS) and contains_any(text, RANT_TRAFFIC_TERMS) and contains_any(text, RANT_LOSS_TERMS):
        return f"{subject}流量来得很随机，卖家很难把曝光稳定变成成交。" if subject else "流量来得很随机，曝光很难稳定变成成交。"
    if contains_any(text, RANT_BRAND_MISMATCH_TERMS):
        return "这类讨论暴露的不是单点运营问题，而是行业默认品牌形象和真实用户人群本身就脱节。"
    if contains_any(text, RANT_RESTRICTION_TERMS) and contains_any(text, RANT_PAID_TERMS):
        return "这类讨论卡的不是创意好不好，而是主流广告渠道本身就不愿意放行这类商品。"
    if contains_any(text, RANT_LOSS_TERMS) and contains_any(text, RANT_PAID_TERMS):
        return f"{subject}内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。" if subject else "大家不是在抱怨流量少，而是在怀疑继续投广告后到底能不能成交。"
    if contains_any(text, RANT_LOSS_TERMS) and contains_any(text, RANT_TRAFFIC_TERMS):
        return f"{subject}内容有流量却卖不动，问题已经落到转化和成交层。" if subject else "讨论已经不只是流量起伏，而是转化和成交起不来的经营问题。"
    if contains_any(text, RANT_LOSS_TERMS):
        return "讨论已经不只是流量起伏，而是转化和成交起不来的经营问题。"
    return None


def build_rant_post_why(
    post: Any,
    *,
    get_payload_value:Optional[ Callable[[Any, str], Any]] = None,
) ->Optional[ str]:
    accessor = get_payload_value or _default_get_payload_value
    text = normalize_text(" ".join([str(accessor(post, "title") or ""), str(accessor(post, "body_preview") or "")]))
    if not text:
        return None
    if contains_any(text, RANT_INSTABILITY_TERMS) and contains_any(text, RANT_TRAFFIC_TERMS) and contains_any(text, RANT_LOSS_TERMS):
        return "这条帖子不是在泛吐槽，而是在说流量来得很随机，曝光很难稳定变成成交。"
    if contains_any(text, RANT_BRAND_MISMATCH_TERMS):
        return "这条帖子暴露的不是单点运营问题，而是行业默认品牌形象和真实用户人群脱节。"
    if contains_any(text, RANT_RESTRICTION_TERMS) and contains_any(text, RANT_PAID_TERMS):
        return "这条帖子暴露的不是素材好不好，而是这类商品在主流广告渠道本身就受限。"
    if contains_any(text, RANT_LOSS_TERMS) and contains_any(text, RANT_PAID_TERMS):
        return "这条帖子不是在抱怨曝光少，而是在怀疑继续投广告后到底能不能成交。"
    if contains_any(text, RANT_LOSS_TERMS) and contains_any(text, RANT_TRAFFIC_TERMS):
        return "这条帖子不是泛聊流量，而是在说有流量却卖不动，问题已经落到成交层。"
    if contains_any(text, RANT_LOSS_TERMS):
        return "这条帖子直接提到转化和销售起不来，问题已经开始影响成交。"
    if contains_any(text, RANT_PAID_TERMS):
        return "这条帖子在质疑投流值不值，大家盯的是付费后到底有没有成交。"
    if contains_any(text, RANT_TRUST_BREAK_TERMS):
        return "这条帖子说的不是单纯不好用，而是宣传、客服答复和到手实物完全对不上，用户会直接怀疑这个品牌能不能信。"
    if contains_any(text, RANT_VALUE_GAP_TERMS):
        return "这条帖子暴露的是预期和实际体验之间的落差。用户不是完全不要，而是买完觉得没有值回预期。"
    if contains_any(text, RANT_EFFORT_GAP_TERMS):
        return "这条帖子在说用户以为买回来就能轻松用，但实际还要补很多经验和额外步骤，门槛比想象高。"
    if int(accessor(post, "num_comments") or 0) >= 5:
        return "这不是一次性吐槽，评论里也有人继续接这个问题。"
    return None


def build_rant_post_relevant(
    post: Any,
    *,
    get_payload_value:Optional[ Callable[[Any, str], Any]] = None,
) ->Optional[ str]:
    accessor = get_payload_value or _default_get_payload_value
    text = normalize_text(" ".join([str(accessor(post, "title") or ""), str(accessor(post, "body_preview") or "")]))
    if not text:
        return None
    if contains_any(text, RANT_TRUST_BREAK_TERMS):
        return "这帖主要在讲宣传、客服承诺和到手体验对不上，抱怨点集中在被误导和不敢再信。"
    if contains_any(text, RANT_VALUE_GAP_TERMS):
        return "这帖主要在讲买前期待很高，但到手后觉得没值回价格，抱怨点集中在效果不达预期。"
    if contains_any(text, RANT_EFFORT_GAP_TERMS):
        return "这帖主要在讲上手和维护比想象中更折腾，抱怨点集中在门槛高、太费心。"
    if contains_any(text, RANT_RESTRICTION_TERMS) and contains_any(text, RANT_PAID_TERMS):
        return "这帖主要在讲这类商品不是不会卖，而是广告渠道本身就在拦，抱怨点集中在放量受限。"
    if contains_any(text, RANT_LOSS_TERMS) and contains_any(text, RANT_TRAFFIC_TERMS):
        return "这帖主要在讲看的人不少，但最后没变成订单，抱怨点集中在流量和成交脱节。"
    if contains_any(text, RANT_LOSS_TERMS):
        return "这帖主要在讲大家不是没兴趣，而是最后没有下单，抱怨点已经落到成交层。"
    if contains_any(text, RANT_BRAND_MISMATCH_TERMS):
        return "这帖主要在讲品牌形象和真实用户不匹配，抱怨点集中在“看起来像给别人做的”。"
    return None
