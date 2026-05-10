from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.hotpost.hotpost_config import load_default_hotpost_runtime_config
from app.services.hotpost.query_resolver import HotpostQueryResolution

_GENERIC_RANT_HINTS = ("抱怨", "吐槽", "差评", "槽点", "不满", "诟病", "被骂")
_GENERIC_SUBPROBLEM_HINTS = (
    "维护",
    "清洗",
    "维修",
    "售后",
    "退款",
    "客服",
    "支付",
    "物流",
    "噪音",
    "漏水",
    "加热",
    "流量",
    "转化",
    "广告",
    "审核",
    "账号",
    "崩溃",
    "卡死",
    "绿屏",
    "听不懂",
    "漏掉",
    "漏掉了",
    "丢失",
    "套话",
    "空话",
)
_BUSINESS_HINTS = ("售卖", "经营", "生意", "品牌", "人群", "商家", "店铺")
_BUSINESS_TERMS = {
    "sell",
    "selling",
    "seller",
    "sellers",
    "business",
    "brand",
    "branding",
    "marketing",
    "customer",
    "customers",
    "payment",
    "payments",
    "compliance",
    "trust",
    "persona",
    "shipping",
    "logistics",
    "channel",
    "channels",
    "reseller",
}
_CONVERSION_TERMS = {"traffic", "view", "views", "click", "clicks", "exposure", "reach", "sales", "sale", "purchase", "purchases", "conversion", "conversions", "buyer", "buyers", "orders", "order"}
_CONVERSION_CONTEXT_TERMS = {
    "traffic",
    "view",
    "views",
    "click",
    "clicks",
    "exposure",
    "reach",
    "content",
    "contents",
    "video",
    "videos",
    "high",
    "low",
    "sale",
    "sales",
    "purchase",
    "purchases",
    "conversion",
    "conversions",
    "buyer",
    "buyers",
    "orders",
    "order",
    "funnel",
}
_PLATFORM_TERMS = {"tiktok", "shopify", "amazon", "etsy", "instagram", "youtube", "facebook", "meta", "ebay"}
_PLATFORM_COMMERCE_TERMS = {
    "ads",
    "ad",
    "shop",
    "seller",
    "sellers",
    "store",
    "stores",
    "merchant",
    "merchants",
    "product",
    "products",
    "gmv",
    "checkout",
    "orders",
    "order",
}
_SUPPORT_HINTS = ("客服", "退款", "售后", "申诉", "对账", "支持")
_SUPPORT_TERMS = {"support", "refund", "refunds", "returns", "appeal", "appeals", "response", "responding", "ticket", "tickets"}
_COMPARISON_TERMS = {"compare", "comparing", "comparison", "vs", "versus", "better", "worse"}
_TRUST_TERMS = {"trust", "scam", "fake", "misleading", "lied", "lie", "counterfeit", "review", "reviews"}
_IDENTITY_TERMS = {"privacy", "private", "discreet", "shame", "embarrassing"}
_TRANSACTION_TERMS = {"payment", "payments", "refund", "refunds", "shipping", "delivery", "compliance", "checkout", "fulfillment", "transaction", "transactions"}
_GENERIC_COMPLAINT_TERMS = {
    "complaint",
    "complaints",
    "complain",
    "complains",
    "complaining",
    "bad",
    "review",
    "reviews",
    "scam",
    "issues",
    "issue",
    "problems",
    "problem",
}
_GENERIC_COMPLAINT_SPECIFIC_ISSUE_TERMS = {
    "crash",
    "crashes",
    "crashing",
    "freeze",
    "freezes",
    "frozen",
    "lag",
    "lags",
    "lagging",
    "bug",
    "bugs",
    "error",
    "errors",
    "broken",
    "broke",
    "outage",
    "update",
    "updates",
    "after update",
}
_SPECIFIC_ISSUE_CONTEXT_TERMS = {
    "crash",
    "crashes",
    "crashing",
    "freeze",
    "freezes",
    "frozen",
    "lag",
    "lags",
    "lagging",
    "slow",
    "slowness",
    "bug",
    "bugs",
    "error",
    "errors",
    "broken",
    "broke",
    "outage",
    "rewrite",
    "rewriting",
    "nonsense",
    "garbage",
    "useless",
}
_PRE_PURCHASE_STAGE_TERMS = {
    "click",
    "clicks",
    "ctr",
    "track",
    "tracking",
    "tracked",
    "pixel",
    "session",
    "sessions",
    "cart",
    "checkout",
    "landing",
    "offer",
}
_META_TERMS = _BUSINESS_TERMS | _CONVERSION_TERMS | _SUPPORT_TERMS | _TRUST_TERMS | _IDENTITY_TERMS | _TRANSACTION_TERMS | _GENERIC_COMPLAINT_TERMS | {"pain", "pains", "point", "points", "challenge", "challenges", "problem", "problems", "issue", "issues", "friction", "frictions", "no"}
_DISALLOWED_NARROWING_TERMS = {"maintenance", "cleaning", "repair", "repairs", "troubleshooting", "setup", "installation", "guide", "tutorial"}
_FRAME_GLUE_TERMS = {
    "how",
    "what",
    "why",
    "when",
    "where",
    "which",
    "who",
    "has",
    "have",
    "had",
    "get",
    "gets",
    "got",
    "does",
    "do",
    "did",
    "doing",
    "about",
    "still",
    "just",
    "really",
    "people",
    "person",
    "most",
    "often",
    "common",
    "no",
}
_SHORT_ANCHOR_HINT_TERMS = {"ai", "ui", "ux", "llm", "gpt"}


@dataclass(frozen=True)
class HotpostProblemFrame:
    mode: str
    query_family: str
    object_terms: list[str]
    primary_friction:Optional[ str] = None
    secondary_frictions: list[str] = field(default_factory=list)
    retrieval_hypotheses: list[str] = field(default_factory=list)
    forbidden_narrowing_terms: list[str] = field(default_factory=list)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = " ".join(str(item or "").strip().lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _tokenize(text: str) -> list[str]:
    pattern = load_default_hotpost_runtime_config().query.keyword_extraction.token_pattern
    return [token.lower() for token in re.compile(pattern).findall(text or "")]


def _frame_stopwords() -> set[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    return {str(item).strip().lower() for item in extraction.stopwords} | _FRAME_GLUE_TERMS


def _filter_frame_terms(tokens: list[str]) -> list[str]:
    stopwords = _frame_stopwords()
    return _dedupe(
        [
            token
            for token in tokens
            if token not in stopwords and token not in _DISALLOWED_NARROWING_TERMS
        ]
    )


def has_hotpost_business_query_hint(query_text: str) -> bool:
    text = str(query_text or "").strip()
    return any(hint in text for hint in _BUSINESS_HINTS) or bool(
        re.search(r"卖[^，。！？?]{0,12}(时|痛点|难点|门槛|挑战|卡点|问题)", text)
    )


def _infer_query_family(*, query_text: str, search_query: str, core_terms: list[str]) -> str:
    lowered = str(query_text or "").lower()
    comparison_markers = (
        " vs ",
        " versus ",
        " compare ",
        " comparison ",
        " better than ",
        " worse than ",
        "相比",
        "比",
        "不如",
        "更偏向",
        "更喜欢",
        "更倾向",
    )
    if (
        any(term in core_terms for term in _COMPARISON_TERMS)
        or (len(core_terms) >= 2 and any(token in lowered for token in comparison_markers))
    ):
        return "comparison_complaint_discovery"
    if any(hint in query_text for hint in _GENERIC_RANT_HINTS) and not any(hint in query_text for hint in _GENERIC_SUBPROBLEM_HINTS):
        return "generic_complaint_discovery"
    if any(hint in query_text for hint in _SUPPORT_HINTS) or any(term in core_terms for term in _SUPPORT_TERMS):
        return "support_breakdown"
    if any(term in core_terms for term in _PLATFORM_TERMS) and any(term in core_terms for term in _CONVERSION_TERMS):
        return "platform_conversion_friction"
    if has_hotpost_business_query_hint(query_text):
        return "business_friction_discovery"
    if any(term in core_terms for term in _CONVERSION_TERMS) and any(term in core_terms for term in {"traffic", "view", "views", "sales", "sale", "purchase", "purchases", "conversion", "conversions"}):
        return "conversion_friction"
    if has_hotpost_business_query_hint(query_text) or any(term in core_terms for term in _BUSINESS_TERMS):
        return "business_friction_discovery"
    if any(
        token in lowered
        for token in (
            "complaint",
            "complaints",
            "complain",
            "complains",
            "complaining",
            "issues",
            "problem",
            "problems",
        )
    ):
        return "generic_complaint_discovery"
    return "specific_issue"


def _object_terms(*, query_text: str, search_query: str, keywords: list[str]) -> list[str]:
    query_tokens = _tokenize(query_text)
    search_tokens = _tokenize(search_query)
    keyword_tokens: list[str] = []
    for keyword in keywords:
        keyword_tokens.extend(_tokenize(keyword))
    keyword_terms = _filter_frame_terms(keyword_tokens)
    query_terms = _filter_frame_terms(query_tokens)
    preferred_terms = _dedupe(keyword_terms + query_terms)
    if len(preferred_terms) >= 2:
        return preferred_terms[:4]
    search_terms = _filter_frame_terms(search_tokens)
    return _dedupe(preferred_terms + search_terms)[:4]


def _forbidden_narrowing_terms(*, query_text: str, search_query: str, keywords: list[str], object_terms: list[str]) -> list[str]:
    query_tokens = set(_tokenize(query_text))
    candidates = _dedupe(_tokenize(search_query) + [token for keyword in keywords for token in _tokenize(keyword)])
    blocked = [
        token
        for token in candidates
        if token not in query_tokens and token not in object_terms and token not in _META_TERMS and token in _DISALLOWED_NARROWING_TERMS
    ]
    return blocked[:4]


def _primary_friction(*, query_family: str, query_text: str, core_terms: list[str]) ->Optional[ str]:
    if query_family in {"conversion_friction", "platform_conversion_friction"}:
        return "weak_buy_reason"
    if query_family == "support_breakdown":
        return "transaction_friction"
    if any(term in core_terms for term in _IDENTITY_TERMS) or any(token in query_text for token in ("隐私", "羞耻", "尴尬")):
        return "identity_friction"
    if any(term in core_terms for term in _TRANSACTION_TERMS) or any(token in query_text for token in ("支付", "物流", "合规")):
        return "transaction_friction"
    if query_family == "generic_complaint_discovery":
        return "trust_gap"
    if query_family == "business_friction_discovery":
        return "weak_buy_reason"
    return None


def _secondary_frictions(*, query_text: str, core_terms: list[str], primary_friction:Optional[ str]) -> list[str]:
    tags: list[str] = []
    if any(term in core_terms for term in _TRUST_TERMS) or any(token in query_text for token in ("不信", "不放心", "虚假", "骗人")):
        tags.append("trust_gap")
    if any(term in core_terms for term in {"sales", "sale", "purchase", "purchases", "conversion", "conversions"}):
        tags.append("weak_buy_reason")
    if any(term in core_terms for term in {"audience", "content", "views", "traffic"}):
        tags.append("wrong_audience")
    if any(term in core_terms for term in _IDENTITY_TERMS) or any(token in query_text for token in ("隐私", "羞耻", "尴尬")):
        tags.append("identity_friction")
    if any(term in core_terms for term in _TRANSACTION_TERMS | _SUPPORT_TERMS) or any(token in query_text for token in ("支付", "物流", "退款", "客服")):
        tags.append("transaction_friction")
    filtered = [tag for tag in _dedupe(tags) if tag != primary_friction]
    return filtered[:2]


def _conversion_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    outcome_terms = {"sale", "sales", "purchase", "purchases", "conversion", "conversions", "buyer", "buyers", "order", "orders", "high", "low"}
    narrowed = [
        term
        for term in object_terms
        if term not in outcome_terms and term not in _DISALLOWED_NARROWING_TERMS
    ]
    if narrowed:
        return narrowed[:3]
    fallback = [
        term
        for term in core_terms
        if term not in outcome_terms and term not in _DISALLOWED_NARROWING_TERMS
    ]
    return fallback[:3]


def _platform_conversion_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    platform = next((term for term in core_terms if term in _PLATFORM_TERMS), "")
    commerce_terms = [
        term
        for term in core_terms
        if term in _PLATFORM_COMMERCE_TERMS and term != platform
    ]
    if commerce_terms:
        return _dedupe([platform, *commerce_terms[:2]]) if platform else _dedupe(commerce_terms[:3])
    return _dedupe([platform, *_conversion_anchor_terms(object_terms, core_terms)[:2]]) if platform else _conversion_anchor_terms(object_terms, core_terms)


def _platform_conversion_stage_hypotheses(core_terms: list[str], anchor_terms: list[str]) -> list[str]:
    platform = next((term for term in anchor_terms if term in _PLATFORM_TERMS), "") or next(
        (term for term in core_terms if term in _PLATFORM_TERMS),
        "",
    )
    if not platform:
        return []
    parts: list[str] = []
    if any(term in core_terms for term in _PRE_PURCHASE_STAGE_TERMS):
        parts.extend(
            [
                f"{platform} ads tracking conversion",
                f"{platform} ads checkout conversion",
            ]
        )
    return _dedupe(parts)


def _support_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    excluded = _SUPPORT_TERMS | {"seller", "sellers", "creator", "creators", "merchant", "merchants", "issue", "issues"}
    anchor = [term for term in object_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    if anchor:
        return anchor[:2]
    fallback = [term for term in core_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    return fallback[:2]


def _generic_complaint_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    excluded = _GENERIC_COMPLAINT_TERMS | {"bad", "scam", "review", "reviews"}
    anchor: list[str] = []
    seen: set[str] = set()
    for term in object_terms:
        if term in excluded or term in _DISALLOWED_NARROWING_TERMS:
            continue
        singular = term[:-1] if term.endswith("s") and len(term) > 3 else term
        plural = f"{term}s" if not term.endswith("s") else term
        if singular in seen or plural in seen:
            continue
        anchor.append(term)
        seen.add(term)
        seen.add(singular)
        seen.add(plural)
    if anchor:
        return anchor[:3]
    fallback = [term for term in core_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    return fallback[:3]


def _business_anchor_terms(core_terms: list[str]) -> list[str]:
    excluded = (
        _BUSINESS_TERMS
        | _SUPPORT_TERMS
        | _TRUST_TERMS
        | _TRANSACTION_TERMS
        | {"conversion", "conversions", "purchase", "purchases", "buyer", "buyers", "order", "orders", "friction", "frictions"}
    )
    anchor = [term for term in core_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    return anchor[:3]


def _comparison_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    excluded = _GENERIC_COMPLAINT_TERMS | _COMPARISON_TERMS | {"users", "user", "people", "person"}
    anchor = [term for term in object_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    if len(anchor) >= 2:
        return anchor[:2]
    fallback = [term for term in core_terms if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS]
    return fallback[:2]


def _comparison_focus_terms(anchor_terms: list[str], core_terms: list[str]) -> list[str]:
    excluded = (
        set(anchor_terms)
        | _GENERIC_COMPLAINT_TERMS
        | _COMPARISON_TERMS
        | {"users", "user", "people", "person"}
    )
    return [
        term
        for term in core_terms
        if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS
    ][:3]


def _specific_issue_anchor_terms(object_terms: list[str], core_terms: list[str]) -> list[str]:
    excluded = _GENERIC_COMPLAINT_TERMS | _COMPARISON_TERMS | _BUSINESS_TERMS | _SUPPORT_TERMS
    entity_terms = [
        term
        for term in object_terms
        if term not in excluded
        and term not in _DISALLOWED_NARROWING_TERMS
        and term not in _SPECIFIC_ISSUE_CONTEXT_TERMS
    ]
    if not entity_terms:
        entity_terms = [
            term
            for term in core_terms
            if term not in excluded
            and term not in _DISALLOWED_NARROWING_TERMS
            and term not in _SPECIFIC_ISSUE_CONTEXT_TERMS
        ]
    if not entity_terms:
        entity_terms = [
            term
            for term in core_terms
            if term not in excluded and term not in _DISALLOWED_NARROWING_TERMS
        ]
    if not entity_terms:
        return []
    short_hints = [
        term
        for term in core_terms
        if term in _SHORT_ANCHOR_HINT_TERMS and term not in entity_terms
    ]
    anchor: list[str] = [entity_terms[0]]
    if short_hints:
        anchor.append(short_hints[0])
    for term in entity_terms[1:]:
        if term not in anchor:
            anchor.append(term)
    return anchor[:3]


def _hypotheses(
    *,
    query_family: str,
    search_query: str,
    object_terms: list[str],
    core_terms: list[str],
    primary_friction:Optional[ str],
) -> list[str]:
    anchor_terms = list(object_terms[:3])
    if query_family == "generic_complaint_discovery":
        anchor_terms = _generic_complaint_anchor_terms(object_terms, core_terms) or anchor_terms
    elif query_family == "platform_conversion_friction":
        anchor_terms = _platform_conversion_anchor_terms(object_terms, core_terms)
    elif query_family == "conversion_friction":
        anchor_terms = _conversion_anchor_terms(object_terms, core_terms)
    elif query_family == "support_breakdown":
        anchor_terms = _support_anchor_terms(object_terms, core_terms) or anchor_terms
    elif query_family == "business_friction_discovery":
        anchor_terms = _business_anchor_terms(core_terms) or anchor_terms
    elif query_family == "comparison_complaint_discovery":
        anchor_terms = _comparison_anchor_terms(object_terms, core_terms) or anchor_terms
    elif query_family == "specific_issue":
        anchor_terms = _specific_issue_anchor_terms(object_terms, core_terms) or anchor_terms
    anchor = " ".join(anchor_terms).strip()
    parts: list[str] = []
    if query_family == "generic_complaint_discovery" and anchor:
        if any(term in search_query for term in _GENERIC_COMPLAINT_SPECIFIC_ISSUE_TERMS):
            parts.append(search_query)
        parts.extend([f"{anchor} complaints", f"{anchor} bad reviews", f"{anchor} scam issues"])
    elif query_family == "platform_conversion_friction" and anchor:
        platform = next((term for term in anchor_terms if term in _PLATFORM_TERMS), anchor_terms[0])
        context_terms = [term for term in anchor_terms if term != platform]
        platform_context = " ".join(_dedupe([platform, *context_terms[:2]])).strip()
        stage_parts = _platform_conversion_stage_hypotheses(core_terms, anchor_terms)
        parts.extend(
            [
                f"{platform} ads no sales",
                *stage_parts,
                f"{platform_context or platform} low conversion",
                f"{platform} seller no orders",
                search_query,
            ]
        )
    elif query_family == "conversion_friction" and anchor:
        compact_anchor = anchor_terms[:1] or object_terms[:1] or core_terms[:1]
        parts.extend(
            [
                f"{anchor} no sales",
                f"{' '.join(compact_anchor).strip()} no purchase conversion",
                search_query,
            ]
        )
    elif query_family == "support_breakdown" and anchor:
        parts.extend([f"{anchor} support issue", f"{anchor} refund issue", search_query])
    elif query_family == "business_friction_discovery" and anchor:
        parts.append(f"{anchor} business challenges")
        if any(term in core_terms for term in {"sales", "sale", "purchase", "purchases", "conversion", "conversions"}):
            conversion_anchor = " ".join(anchor_terms[:2]).strip() or anchor
            parts.append(f"{conversion_anchor} no sales")
        if primary_friction == "transaction_friction":
            parts.append(f"{anchor} payment trust issue")
        parts.append(search_query)
    elif query_family == "comparison_complaint_discovery":
        if len(anchor_terms) >= 2:
            left = anchor_terms[0]
            right = anchor_terms[1]
            focus = " ".join(_comparison_focus_terms(anchor_terms, core_terms)[:2]).strip()
            parts.extend(
                [
                    f"{left} {' '.join(filter(None, [focus, 'better than', right]))}".strip(),
                    f"{right} {' '.join(filter(None, [focus, 'worse than', left]))}".strip(),
                    (
                        f"{left} vs {right} {focus} complaints".strip()
                        if focus
                        else f"{left} vs {right} complaints"
                    ),
                    search_query,
                ]
            )
        elif anchor:
            parts.extend([f"{anchor} comparison complaints", search_query])
        else:
            parts.append(search_query)
    elif query_family == "specific_issue" and anchor:
        issue_terms = [
            term
            for term in core_terms
            if term in _SPECIFIC_ISSUE_CONTEXT_TERMS and term not in set(anchor_terms)
        ]
        anchor_short_hints = [
            term for term in anchor_terms if term in _SHORT_ANCHOR_HINT_TERMS
        ]
        short_hints = [
            term
            for term in core_terms
            if term in _SHORT_ANCHOR_HINT_TERMS and term not in set(anchor_terms)
        ]
        if anchor_short_hints and len(anchor_terms) >= 2:
            parts.append(" ".join(anchor_terms[:2]))
        if short_hints and anchor_terms:
            parts.append(f"{anchor_terms[0]} {short_hints[0]}")
        parts.extend([f"{anchor} issue", f"{anchor} complaints"])
        if issue_terms:
            parts.append(f"{anchor} {issue_terms[0]}")
        parts.append(search_query)
    else:
        parts.append(search_query)
    return _dedupe(parts)


def build_hotpost_problem_frame(*, mode: str, resolution: HotpostQueryResolution, core_terms: list[str]) -> HotpostProblemFrame:
    normalized_mode = str(mode or "trending").strip().lower()
    original_query = str(getattr(resolution, "original_query", "") or "").strip()
    search_query = str(resolution.search_query or original_query).strip().lower()
    if normalized_mode != "rant":
        return HotpostProblemFrame(mode=normalized_mode, query_family=f"{normalized_mode}_discovery", object_terms=core_terms[:4], retrieval_hypotheses=[search_query] if search_query else [])
    object_terms = _object_terms(query_text=original_query, search_query=search_query, keywords=resolution.keywords)
    query_family = _infer_query_family(query_text=original_query, search_query=search_query, core_terms=core_terms)
    forbidden_narrowing_terms = _forbidden_narrowing_terms(query_text=original_query, search_query=search_query, keywords=resolution.keywords, object_terms=object_terms)
    primary_friction = _primary_friction(query_family=query_family, query_text=original_query, core_terms=core_terms)
    secondary_frictions = _secondary_frictions(query_text=original_query, core_terms=core_terms, primary_friction=primary_friction)
    retrieval_hypotheses = _hypotheses(
        query_family=query_family,
        search_query=search_query,
        object_terms=object_terms or core_terms[:3],
        core_terms=core_terms,
        primary_friction=primary_friction,
    )
    return HotpostProblemFrame(
        mode=normalized_mode,
        query_family=query_family,
        object_terms=object_terms or core_terms[:4],
        primary_friction=primary_friction,
        secondary_frictions=secondary_frictions,
        retrieval_hypotheses=retrieval_hypotheses,
        forbidden_narrowing_terms=forbidden_narrowing_terms,
    )


__all__ = ["HotpostProblemFrame", "build_hotpost_problem_frame", "has_hotpost_business_query_hint"]
