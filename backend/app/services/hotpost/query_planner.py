from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.hotpost.hotpost_config import load_default_hotpost_runtime_config
from app.services.hotpost.problem_frame import build_hotpost_problem_frame, has_hotpost_business_query_hint
from app.services.hotpost.query_resolver import HotpostQueryResolution
from app.utils.subreddit import normalize_subreddit_name

_RANT_GENERIC_PROBLEM_TERMS = {
    "pain",
    "pains",
    "point",
    "points",
    "issue",
    "issues",
    "problem",
    "problems",
    "challenge",
    "challenges",
    "complaint",
    "complaints",
}
_RANT_BUSINESS_CONTEXT_TERMS = {
    "sell",
    "selling",
    "seller",
    "sellers",
    "business",
    "brand",
    "branding",
    "marketing",
    "market",
    "customer",
    "customers",
    "payment",
    "payments",
    "compliance",
    "trust",
    "persona",
    "shipping",
    "logistics",
    "policy",
    "policies",
    "restriction",
    "restrictions",
    "channel",
    "channels",
    "reseller",
    "unauthorized",
}
_RANT_BUSINESS_CONTEXT_HINTS = ("售卖", "经营", "生意", "品牌", "人群", "用户", "客户")
_RANT_BUSINESS_COMMUNITIES = ["r/smallbusiness", "r/ecommerce", "r/entrepreneur"]
_RANT_PLATFORM_TERMS = {"tiktok", "shopify", "amazon", "etsy", "instagram", "youtube", "facebook", "meta", "ebay"}
_SHORT_HINT_TOKENS = {"ai", "ui", "ux", "llm", "gpt"}
_OBJECT_SUBREDDIT_STOPWORDS = _RANT_GENERIC_PROBLEM_TERMS | {
    "app",
    "bad",
    "better",
    "bug",
    "bugs",
    "complain",
    "complains",
    "complaints",
    "empty",
    "easier",
    "fluff",
    "garbage",
    "generic",
    "issue",
    "issues",
    "nonsense",
    "overall",
    "people",
    "most",
    "lately",
    "long",
    "notes",
    "output",
    "verbose",
    "concise",
    "problem",
    "problems",
    "rewrite",
    "rewriting",
    "say",
    "same",
    "short",
    "sync",
    "timeline",
    "word",
    "words",
    "use",
    "users",
    "why",
}
_QUERY_PART_BUDGET_BY_FAMILY = {
    "platform_conversion_friction": 3,
    "support_breakdown": 3,
    "specific_issue": 4,
    "comparison_complaint_discovery": 4,
}


@dataclass(frozen=True)
class HotpostQueryPlan:
    query_intent: str
    query_family: str
    core_terms: list[str]
    expanded_terms: list[str]
    negative_terms: list[str]
    candidate_subreddits: list[str]
    positive_intent_terms: list[str]
    forbidden_context_terms: list[str]
    domain_terms: list[str]
    strict_domain_terms: list[str]
    alias_terms: list[str]
    strict_anchor_min_hits: int
    search_strategy: str
    query_parts: list[str]
    primary_friction:Optional[ str] = None
    secondary_frictions:Optional[ list[str]] = None
    retrieval_hypotheses:Optional[ list[str]] = None
    forbidden_narrowing_terms:Optional[ list[str]] = None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        text = " ".join(str(item or "").strip().lower().split())
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _tokenize(text: str) -> list[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    return [token.lower() for token in re.compile(extraction.token_pattern).findall(text or "")]


def _core_terms_from_search_query(search_query: str) -> list[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    stopwords = {str(item).strip().lower() for item in extraction.stopwords}
    return _dedupe(
        [
            token
            for token in _tokenize(search_query)
            if token not in stopwords and len(token) >= extraction.min_length
        ]
    )


def _core_terms_from_resolution_keywords(keywords: list[str]) -> list[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    stopwords = {str(item).strip().lower() for item in extraction.stopwords}
    tokens: list[str] = []
    for keyword in keywords:
        tokens.extend(_tokenize(keyword))
    return _dedupe(
        [
            token
            for token in tokens
            if token not in stopwords and len(token) >= extraction.min_length
        ]
    )


def _short_hint_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]{2,4}", str(text or "").lower())
    return _dedupe([token for token in tokens if token in _SHORT_HINT_TOKENS])


def _phrase_terms(core_terms: list[str]) -> list[str]:
    phrases: list[str] = []
    for size in (2, 3):
        for idx in range(0, max(0, len(core_terms) - size + 1)):
            phrases.append(" ".join(core_terms[idx : idx + size]))
    return phrases


def _compact_rant_problem_query(core_terms: list[str]) -> str:
    if not core_terms:
        return ""
    primary = core_terms[0]
    generic_terms = {"traffic", "content", "video", "videos", "views", "view", "high", "low"}
    secondary = [term for term in core_terms[1:] if term not in generic_terms]
    if not secondary:
        return ""
    has_purchase = any(term in {"purchase", "purchases", "buyer", "buyers", "order", "orders"} for term in secondary)
    has_sales = any(term in {"sale", "sales", "revenue"} for term in secondary)
    has_conversion = any(term in {"conversion", "conversions", "convert", "converting"} for term in secondary)
    if has_purchase and has_conversion:
        prioritized = ["purchase", "conversion"]
    elif has_sales and has_conversion:
        prioritized = ["sales", "conversion"]
    elif has_purchase:
        prioritized = ["purchase"]
    elif has_sales:
        prioritized = ["sales"]
    elif has_conversion:
        prioritized = ["conversion"]
    else:
        return ""
    compact_terms = _dedupe(["no"] + prioritized)[:3]
    return " ".join([primary, *compact_terms]) if len(compact_terms) >= 2 else ""


def _normalize_rant_core_terms(core_terms: list[str]) -> list[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    stopwords = {str(item).strip().lower() for item in extraction.stopwords}
    filtered = [
        term
        for term in core_terms
        if term not in _RANT_GENERIC_PROBLEM_TERMS and term not in stopwords
    ]
    return filtered or core_terms


def _looks_like_business_rant(query_text: str, core_terms: list[str]) -> bool:
    query_lower = str(query_text or "").lower()
    return any(term in core_terms for term in _RANT_BUSINESS_CONTEXT_TERMS) or has_hotpost_business_query_hint(
        query_lower
    )


def _business_rant_query(query_text: str, core_terms: list[str]) -> str:
    if not _looks_like_business_rant(query_text, core_terms):
        return ""
    anchor_terms = [
        term
        for term in core_terms
        if term not in _RANT_GENERIC_PROBLEM_TERMS and term not in _RANT_BUSINESS_CONTEXT_TERMS
    ]
    if not anchor_terms:
        return ""
    return f"{' '.join(anchor_terms[:3])} business challenges"


def _alias_terms(query_text: str, core_terms: list[str], alias_map: dict[str, list[str]]) -> list[str]:
    query_lower = str(query_text or "").lower()
    matched: list[str] = []
    for key, values in alias_map.items():
        if key in query_lower or key in core_terms:
            matched.extend(values)
    return _dedupe(matched)


def _alias_core_terms(alias_terms: list[str]) -> list[str]:
    extraction = load_default_hotpost_runtime_config().query.keyword_extraction
    stopwords = {str(item).strip().lower() for item in extraction.stopwords}
    stopwords.update({"no", "low", "high"})
    tokens: list[str] = []
    for alias in alias_terms:
        tokens.extend(_tokenize(alias))
    return _dedupe(
        [
            token
            for token in tokens
            if token not in stopwords and len(token) >= extraction.min_length
        ]
    )


def _rant_subreddit_anchor_terms(core_terms: list[str]) -> list[str]:
    anchored = [
        term
        for term in core_terms
        if len(term) >= 3 and term not in _OBJECT_SUBREDDIT_STOPWORDS
    ]
    if anchored:
        return anchored[:2]
    return [term for term in core_terms if len(term) >= 4][:1]


def _filter_rant_subreddits(
    subreddits: list[str],
    core_terms: list[str],
) -> list[str]:
    normalized = _dedupe([normalize_subreddit_name(name) for name in subreddits])
    anchor_terms = _rant_subreddit_anchor_terms(core_terms)
    if not normalized or not anchor_terms:
        return normalized
    matched = [
        subreddit
        for subreddit in normalized
        if any(term in subreddit.replace("r/", "") for term in anchor_terms)
    ]
    return matched or normalized


def _platform_rant_subreddits(core_terms: list[str], query_family: str) -> list[str]:
    if query_family != "platform_conversion_friction":
        return []
    platform = next((term for term in core_terms if term in _RANT_PLATFORM_TERMS), "")
    if not platform:
        return []
    return _dedupe(
        [
            normalize_subreddit_name(f"r/{platform}"),
            normalize_subreddit_name(f"r/{platform}ads"),
            normalize_subreddit_name(f"r/{platform}shop"),
            normalize_subreddit_name(f"r/{platform}help"),
        ]
    )


def _object_anchor_subreddits(*, core_terms: list[str], query_family: str, query_text: str) -> list[str]:
    if query_family in {"platform_conversion_friction", "business_friction_discovery", "conversion_friction"}:
        return []
    if _looks_like_business_rant(query_text, core_terms):
        return []
    object_terms = _rant_subreddit_anchor_terms(core_terms)
    if not object_terms:
        return []
    if query_family == "comparison_complaint_discovery":
        return _dedupe([normalize_subreddit_name(f"r/{term}") for term in object_terms[:2] if term])[:2]

    variants: list[str] = []
    primary = object_terms[0]
    variants.append(primary)
    short_hints = [token for token in _short_hint_tokens(query_text) if token in _SHORT_HINT_TOKENS]
    if short_hints:
        variants.extend([f"{primary}{short_hints[0]}", f"{primary}_{short_hints[0]}"])
    if len(object_terms) >= 2:
        secondary = object_terms[1]
        if secondary not in _OBJECT_SUBREDDIT_STOPWORDS:
            variants.append(secondary)
        variants.extend([f"{primary}{secondary}", f"{primary}_{secondary}"])
    return _dedupe([normalize_subreddit_name(f"r/{variant}") for variant in variants if variant])[:4]


def _should_defer_rant_default_subreddits(
    *,
    query_family: str,
    resolved_subreddits: list[str],
) -> bool:
    return query_family in {
        "generic_complaint_discovery",
        "platform_conversion_friction",
        "support_breakdown",
        "specific_issue",
        "comparison_complaint_discovery",
    } and not resolved_subreddits


def _trim_rant_strict_terms(strict_terms: list[str], candidate_subreddits: list[str]) -> list[str]:
    if len(strict_terms) <= 1 or not candidate_subreddits:
        return strict_terms
    subreddit_names = [subreddit.replace("r/", "") for subreddit in candidate_subreddits]
    narrowed = [
        term
        for term in strict_terms
        if not any(term in subreddit_name for subreddit_name in subreddit_names)
    ]
    return narrowed or strict_terms


def _query_part_budget(*, query_family: str, default: int) -> int:
    return max(1, _QUERY_PART_BUDGET_BY_FAMILY.get(query_family, int(default)))


def _comparison_focus_terms(core_terms: list[str]) -> list[str]:
    if len(core_terms) <= 2:
        return []
    return [
        term
        for term in core_terms[2:]
        if term not in _RANT_GENERIC_PROBLEM_TERMS
    ][:3]


def _mode_query_parts(
    mode: str,
    query_family:Optional[ str],
    query_text: str,
    search_query: str,
    core_terms: list[str],
    mode_terms: list[str],
    alias_terms: list[str],
) -> list[str]:
    parts: list[str] = []
    if mode == "rant" and query_family == "comparison_complaint_discovery" and len(core_terms) >= 2:
        left = core_terms[0]
        right = core_terms[1]
        focus = " ".join(_comparison_focus_terms(core_terms)[:2]).strip()
        if focus:
            parts.extend(
                [
                    f"{left} {focus} better than {right}",
                    f"prefer {left} over {right} for {focus}",
                    f"{right} {focus} worse than {left}",
                    f"switched from {right} to {left} for {focus}",
                    f"{left} vs {right} {focus} complaints",
                ]
            )
        else:
            parts.extend(
                [
                    f"{left} better than {right}",
                    f"prefer {left} over {right}",
                    f"{right} worse than {left}",
                    f"switched from {right} to {left}",
                    f"{left} vs {right} complaints",
                ]
            )
        parts.append(search_query.strip().lower())
        return _dedupe(parts)
    if mode == "rant" and core_terms:
        business_query = _business_rant_query(query_text, core_terms)
        prefer_business_query = bool(
            business_query and not any(term in _RANT_PLATFORM_TERMS for term in core_terms)
        )
        if prefer_business_query:
            parts.append(business_query)
        alias_prefix = " ".join(core_terms[:2]) if len(core_terms) >= 2 else core_terms[0]
        if alias_terms:
            alias_query = alias_terms[0]
            if alias_prefix and alias_prefix not in alias_query:
                parts.append(f"{alias_prefix} {alias_query}".strip())
            else:
                parts.append(alias_query)
        compact_query = _compact_rant_problem_query(core_terms)
        if compact_query:
            parts.append(compact_query)
        if business_query and not prefer_business_query:
            parts.append(business_query)
        parts.append(search_query.strip().lower())
        if query_family == "specific_issue":
            short_hints = [term for term in core_terms if term in _SHORT_HINT_TOKENS]
            if short_hints and core_terms:
                parts.append(" ".join([core_terms[0], short_hints[0]]).strip())
        anchor_size = min(3, len(core_terms))
        anchor = " ".join(core_terms[:anchor_size])
        parts.append(anchor)
        for suffix in mode_terms:
            parts.append(f"{anchor} {suffix}".strip())
    else:
        parts.extend(alias_terms)
        parts.append(search_query.strip().lower())
        if len(core_terms) >= 2:
            parts.append(" ".join(core_terms[:2]))
    if mode == "opportunity" and core_terms:
        anchor = " ".join(core_terms[:2]) if len(core_terms) >= 2 else core_terms[0]
        for suffix in mode_terms:
            if " " in suffix:
                parts.append(f"{suffix} {anchor}".strip())
            else:
                parts.append(f"{anchor} {suffix}".strip())
    elif mode != "rant":
        parts.extend(_phrase_terms(core_terms))
        for suffix in mode_terms:
            anchor = " ".join(core_terms[:2]) if len(core_terms) >= 2 else search_query.strip().lower()
            parts.append(f"{anchor} {suffix}".strip())
    return _dedupe(parts)


def _semantic_terms(
    *,
    mode: str,
    planner: object,
    query_text: str,
    core_terms: list[str],
) -> tuple[list[str], list[str], list[str], list[str], int]:
    query_lower = str(query_text or "").lower()
    positive_candidates = list(getattr(planner, "positive_intent_terms", {}).get(mode, []))
    forbidden_candidates = list(getattr(planner, "forbidden_context_terms", {}).get(mode, []))
    domain_candidates = list(getattr(planner, "domain_terms", {}).get(mode, []))
    strict_candidates = list(getattr(planner, "strict_domain_terms", {}).get(mode, []))
    strict_min_hits = int(getattr(planner, "strict_anchor_min_hits", {}).get(mode, 0))
    generic_terms = set(getattr(planner, "noise_terms", []))

    positive_terms = _dedupe(
        [term for term in positive_candidates if term in query_lower or term in core_terms] or positive_candidates[:3]
    )[:4]
    forbidden_terms = _dedupe(forbidden_candidates)[:6]
    matched_domain_terms = [term for term in domain_candidates if term in query_lower or term in core_terms]
    fallback_domain_terms = [
        term for term in core_terms if term not in generic_terms and term not in positive_terms
    ]
    domain_terms = _dedupe(matched_domain_terms + fallback_domain_terms)[:4]
    strict_domain_terms = _dedupe(
        [term for term in strict_candidates if term in query_lower or term in core_terms]
    )[:4]
    if mode == "rant" and not strict_domain_terms:
        strict_domain_terms = _dedupe(matched_domain_terms + fallback_domain_terms)[:4]
        if strict_domain_terms:
            strict_min_hits = max(strict_min_hits, 1)
    return positive_terms, forbidden_terms, domain_terms, strict_domain_terms, strict_min_hits


def build_hotpost_query_plan(*, mode: str, resolution: HotpostQueryResolution) -> HotpostQueryPlan:
    runtime = load_default_hotpost_runtime_config().query.planner
    normalized_mode = str(mode or "trending").strip().lower()
    original_query = str(getattr(resolution, "original_query", "") or "").strip()
    search_query = str(getattr(resolution, "search_query", "") or original_query).strip()
    keyword_values = list(getattr(resolution, "keywords", []) or [])
    subreddit_values = list(getattr(resolution, "subreddits", []) or [])
    resolved_keywords = _dedupe([str(term).lower() for term in keyword_values])
    resolved_keyword_terms = _core_terms_from_resolution_keywords(resolved_keywords)
    if normalized_mode == "rant":
        core_terms = resolved_keyword_terms or _core_terms_from_search_query(search_query) or _dedupe(_tokenize(search_query))
        core_terms = _dedupe(core_terms + _short_hint_tokens(original_query or search_query))
        core_terms = _normalize_rant_core_terms(core_terms)
    else:
        core_terms = _core_terms_from_search_query(search_query) or resolved_keyword_terms or _dedupe(_tokenize(search_query))
    problem_frame = build_hotpost_problem_frame(
        mode=normalized_mode,
        resolution=resolution,
        core_terms=core_terms,
    )
    if normalized_mode == "rant" and problem_frame.forbidden_narrowing_terms:
        core_terms = [term for term in core_terms if term not in set(problem_frame.forbidden_narrowing_terms)] or core_terms
    raw_tokens = _tokenize(original_query or search_query)
    allowed = set(core_terms)
    noise_terms = set(runtime.noise_terms)
    negative_terms = _dedupe([token for token in raw_tokens if token in noise_terms or token not in allowed])[
        : runtime.max_negative_terms
    ]
    mode_terms = _dedupe(runtime.mode_terms.get(normalized_mode, []))
    alias_terms = _alias_terms(original_query or search_query, core_terms, runtime.term_aliases)
    alias_core_terms = _alias_core_terms(alias_terms)
    expanded_terms = _dedupe(alias_terms + alias_core_terms + mode_terms + resolved_keywords + _phrase_terms(core_terms))[
        : runtime.max_expanded_terms
    ]
    resolved_subreddits = [normalize_subreddit_name(name) for name in subreddit_values]
    if normalized_mode == "rant":
        resolved_subreddits = _filter_rant_subreddits(resolved_subreddits, core_terms)
    platform_subreddits = (
        _platform_rant_subreddits(core_terms, problem_frame.query_family)
        if normalized_mode == "rant"
        else []
    )
    default_subreddits = [normalize_subreddit_name(name) for name in runtime.candidate_subreddits.get(normalized_mode, [])]
    if (
        normalized_mode == "rant"
        and problem_frame.query_family != "platform_conversion_friction"
        and _looks_like_business_rant(original_query or search_query, core_terms)
    ):
        default_subreddits = list(_RANT_BUSINESS_COMMUNITIES)
    defer_default_subreddits = (
        _should_defer_rant_default_subreddits(
            query_family=problem_frame.query_family,
            resolved_subreddits=resolved_subreddits,
        )
        if normalized_mode == "rant"
        else False
    )
    suppress_default_subreddits = (
        normalized_mode == "rant"
        and problem_frame.query_family != "comparison_complaint_discovery"
        and (
            defer_default_subreddits
            or (resolved_subreddits and not _looks_like_business_rant(original_query or search_query, core_terms))
        )
    )
    candidate_subreddits = _dedupe(
        (
            _object_anchor_subreddits(
                core_terms=core_terms,
                query_family=problem_frame.query_family,
                query_text=original_query or search_query,
            )
            if normalized_mode == "rant"
            else []
        )
        + platform_subreddits
        + resolved_subreddits
        + ([] if suppress_default_subreddits else default_subreddits)
    )
    positive_intent_terms, forbidden_context_terms, domain_terms, strict_domain_terms, strict_anchor_min_hits = _semantic_terms(
        mode=normalized_mode,
        planner=runtime,
        query_text=original_query or search_query,
        core_terms=core_terms,
    )
    if normalized_mode == "rant":
        domain_terms = _dedupe(alias_core_terms + domain_terms)[:4]
        strict_domain_terms = _dedupe(alias_core_terms + strict_domain_terms)[:4]
        strict_domain_terms = _trim_rant_strict_terms(strict_domain_terms, candidate_subreddits)
    query_parts = _mode_query_parts(
        normalized_mode,
        problem_frame.query_family,
        original_query or search_query,
        search_query,
        core_terms,
        mode_terms,
        alias_terms,
    )
    if normalized_mode == "rant":
        # Compare queries must prioritize the planner's two-sided query parts.
        # Older retrieval hypotheses are kept only as fallback fill, otherwise they
        # occupy the entire family budget and crowd out the balanced compare forms.
        if problem_frame.query_family == "comparison_complaint_discovery":
            query_parts = query_parts + list(problem_frame.retrieval_hypotheses or [])
        else:
            query_parts = list(problem_frame.retrieval_hypotheses or []) + query_parts
    query_parts = _dedupe(query_parts)[
        : _query_part_budget(query_family=problem_frame.query_family, default=runtime.max_query_parts)
    ]
    search_strategy = runtime.strategy_by_mode.get(normalized_mode, "global-first")
    if normalized_mode == "rant" and problem_frame.query_family == "comparison_complaint_discovery":
        search_strategy = "global-first"
    return HotpostQueryPlan(
        query_intent=runtime.intent_labels.get(normalized_mode, "discovery"),
        query_family=problem_frame.query_family,
        core_terms=core_terms,
        expanded_terms=expanded_terms,
        negative_terms=negative_terms,
        candidate_subreddits=candidate_subreddits,
        positive_intent_terms=positive_intent_terms,
        forbidden_context_terms=forbidden_context_terms,
        domain_terms=domain_terms,
        strict_domain_terms=strict_domain_terms,
        alias_terms=alias_terms,
        strict_anchor_min_hits=strict_anchor_min_hits,
        search_strategy=search_strategy,
        query_parts=query_parts or [search_query.strip().lower()],
        primary_friction=problem_frame.primary_friction,
        secondary_frictions=list(problem_frame.secondary_frictions or []),
        retrieval_hypotheses=list(problem_frame.retrieval_hypotheses or []),
        forbidden_narrowing_terms=list(problem_frame.forbidden_narrowing_terms or []),
    )


__all__ = ["HotpostQueryPlan", "build_hotpost_query_plan"]
