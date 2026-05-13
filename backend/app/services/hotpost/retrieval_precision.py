from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Optional, Any

import yaml

_RANT_GENERIC_COMPLAINT_TERMS = ["complaint", "complaints", "bad review", "bad reviews", "scam", "misleading", "lied", "issue", "issues", "problem", "problems"]
_RANT_TRUST_TERMS = ["trust", "scam", "fake", "misleading", "lied", "review", "reviews"]
_RANT_BUY_REASON_TERMS = ["no sales", "no purchase", "purchase", "sales", "conversion", "conversions", "buyers", "revenue"]
_RANT_TRANSACTION_TERMS = ["payment", "refund", "refunds", "shipping", "delivery", "checkout", "compliance", "support", "ticket"]
_RANT_PLATFORM_COMMERCE_TERMS = ["ads", "ad", "shop", "seller", "sellers", "store", "stores", "merchant", "merchants", "offer"]
_RANT_REQUEST_HELP_TERMS = [
    "reach out",
    "can someone",
    "can somebody",
    "any advice",
    "message me",
    "dm me",
    "audit my",
    "looking for help",
    "need help",
    "agency",
]
_RANT_PRE_PURCHASE_CONVERSION_TERMS = [
    "click",
    "clicks",
    "ctr",
    "conversion",
    "conversions",
    "track",
    "tracking",
    "tracked",
    "pixel",
    "session",
    "sessions",
    "cart",
    "checkout",
    "landing page",
    "landing",
]
_RANT_POST_PURCHASE_FRICTION_TERMS = [
    "refund",
    "refunded",
    "return",
    "returned",
    "shipping",
    "shipped",
    "delivery",
    "delivered",
    "arrived",
    "package",
    "fulfillment",
    "cancelled order",
    "canceled order",
    "scam",
]
_VOICE_COMPLAINT_EVIDENCE_TERMS = [
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
    "sluggish",
    "bug",
    "bugs",
    "error",
    "errors",
    "broken",
    "broke",
    "unusable",
    "useless",
    "garbage",
    "nonsense",
    "rewrite",
    "rewriting",
    "ignore",
    "ignores",
    "ignored",
    "miss",
    "misses",
    "missing",
    "instruction",
    "instructions",
    "sync",
    "syncing",
    "unsynced",
    "out of sync",
    "unreliable",
    "unstable",
]
_VOICE_COMPARE_EVIDENCE_TERMS = [
    "better than",
    "follows the whole brief",
    "full brief",
    "instruction following",
    "instructions better",
    "intent",
    "keeps constraints",
    "long instructions",
    "prefer",
    "rewrites the task",
    "understand instructions",
    "understands",
]
_RANT_COMPARISON_HINTS = (
    " vs ",
    " versus ",
    " compare ",
    " comparison ",
    " better than ",
    " worse than ",
    "比",
    "不如",
    "更好",
    "更差",
    "对比",
    "比较",
)
_COMPARE_ENTITY_IGNORE_TERMS = {
    "alternative",
    "alternatives",
    "llm",
    "llms",
    "model",
    "models",
    "most",
    "other",
    "others",
    "tool",
    "tools",
}
_RANT_SUBJECT_STOP_TERMS = {
    "complaint",
    "complaints",
    "complain",
    "complains",
    "complaining",
    "issue",
    "issues",
    "problem",
    "problems",
    "bad",
    "review",
    "reviews",
    "scam",
    "support",
    "help",
    "refund",
    "refunds",
    "return",
    "returns",
    "no",
    "low",
    "high",
}


@dataclass(frozen=True)
class RetrievalPrecisionConfig:
    trusted_subreddit_terms: dict[str, list[str]]
    suspicious_subreddit_terms: list[str]
    suspicious_title_terms: list[str]
    suspicious_body_terms: list[str]
    generic_query_terms: list[str]
    trusted_source_boost: float
    unknown_source_penalty: float
    required_focus_hits_for_opportunity: int
    suspicious_source_block: bool


@dataclass(frozen=True)
class RetrievalPrecisionDecision:
    source_quality: str
    blocked: bool
    keep: bool
    score: float
    direct_hits: int
    focus_hits: int
    reason: str


def _normalize_terms(values:Optional[ list[Any]]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values or []:
        term = " ".join(str(raw or "").strip().lower().split())
        if not term or term in seen:
            continue
        seen.add(term)
        output.append(term)
    return output


@lru_cache(maxsize=1)
def load_retrieval_precision_config() -> RetrievalPrecisionConfig:
    path = Path(__file__).resolve().parents[3] / "config" / "hotpost_quality.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = dict(payload.get("retrieval_precision") or {})
    return RetrievalPrecisionConfig(
        trusted_subreddit_terms={
            str(key).strip().lower(): _normalize_terms(value)
            for key, value in dict(raw.get("trusted_subreddit_terms") or {}).items()
        },
        suspicious_subreddit_terms=_normalize_terms(raw.get("suspicious_subreddit_terms")),
        suspicious_title_terms=_normalize_terms(raw.get("suspicious_title_terms")),
        suspicious_body_terms=_normalize_terms(raw.get("suspicious_body_terms")),
        generic_query_terms=_normalize_terms(raw.get("generic_query_terms")),
        trusted_source_boost=float(raw.get("trusted_source_boost") or 4.0),
        unknown_source_penalty=float(raw.get("unknown_source_penalty") or 1.5),
        required_focus_hits_for_opportunity=max(
            1, int(raw.get("required_focus_hits_for_opportunity") or 1)
        ),
        suspicious_source_block=str(raw.get("suspicious_source_block", True)).lower() in {"1", "true", "yes"},
    )


def _hit_terms(text:Optional[ str], query_terms: list[str]) -> list[str]:
    haystack = str(text or "").lower()
    return [term for term in query_terms if term in haystack]


def _dedupe_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values:
        term = " ".join(str(raw or "").strip().lower().split())
        if not term or term in seen:
            continue
        seen.add(term)
        output.append(term)
    return output


def _contains_any(text: str, terms: list[str]) -> bool:
    haystack = str(text or "").lower()
    return any(term in haystack for term in terms)


def _collect_hits(*, texts: list[str], terms: list[str]) -> list[str]:
    return sorted({hit for text in texts for hit in _hit_terms(text, terms)})


def _has_comparison_intent(*, request_query:Optional[ str], query_terms: list[str]) -> bool:
    query_text = f" {str(request_query or '').lower()} "
    if any(hint in query_text for hint in _RANT_COMPARISON_HINTS):
        return True
    terms_text = f" {' '.join(query_terms).lower()} "
    return any(hint in terms_text for hint in (" vs ", " versus ", " compare ", " comparison "))


def _requested_compare_entities(
    *,
    query_terms: list[str],
    domain_terms: list[str],
    strict_domain_terms: list[str],
) -> list[str]:
    pool = list(strict_domain_terms or domain_terms or query_terms)
    stop_terms = (
        _RANT_SUBJECT_STOP_TERMS
        | set(_RANT_BUY_REASON_TERMS)
        | set(_RANT_TRANSACTION_TERMS)
        | {"instruction", "instructions", "following", "follow", "long"}
    )
    return _dedupe_terms([term for term in pool if term not in stop_terms])[:2]


def _extract_explicit_compare_entities(text: str) -> list[str]:
    patterns = (
        r"\b([a-z0-9][a-z0-9._+-]{1,})\s+(?:vs|versus)\s+([a-z0-9][a-z0-9._+-]{1,})\b",
        r"\bprefer\s+([a-z0-9][a-z0-9._+-]{1,})\s+over\s+([a-z0-9][a-z0-9._+-]{1,})\b",
    )
    hits: list[str] = []
    lowered = str(text or "").lower()
    for pattern in patterns:
        for left, right in re.findall(pattern, lowered):
            for term in (left, right):
                if term in _RANT_SUBJECT_STOP_TERMS or term in _COMPARE_ENTITY_IGNORE_TERMS:
                    continue
                hits.append(term)
    return _dedupe_terms(hits)


def _subject_anchor_terms(
    *,
    query_terms: list[str],
    domain_terms: list[str],
    strict_domain_terms: list[str],
) -> list[str]:
    pool = list(strict_domain_terms or domain_terms or query_terms)
    stop_terms = _RANT_SUBJECT_STOP_TERMS | set(_RANT_BUY_REASON_TERMS) | set(_RANT_TRANSACTION_TERMS)
    return _dedupe_terms([term for term in pool if term not in stop_terms])


def _pain_anchor_terms(*, query_terms: list[str], positive_intent_terms: list[str]) -> list[str]:
    pain_terms = (
        set(_RANT_GENERIC_COMPLAINT_TERMS)
        | set(_RANT_TRUST_TERMS)
        | set(_RANT_BUY_REASON_TERMS)
        | set(_RANT_TRANSACTION_TERMS)
        | {"complain", "complains", "complaining", "frustrated", "frustrating", "worst", "broken", "expensive"}
    )
    return _dedupe_terms(
        [term for term in [*query_terms, *positive_intent_terms] if term in pain_terms]
    )


def _specific_issue_symptom_terms(
    *,
    query_terms: list[str],
    subject_terms: list[str],
    pain_terms: list[str],
    positive_intent_terms: list[str],
) -> list[str]:
    stop_terms = (
        _RANT_SUBJECT_STOP_TERMS
        | set(_RANT_GENERIC_COMPLAINT_TERMS)
        | set(_RANT_TRUST_TERMS)
        | set(_RANT_BUY_REASON_TERMS)
        | set(_RANT_TRANSACTION_TERMS)
        | set(positive_intent_terms)
    )
    return _dedupe_terms(
        [
            term
            for term in query_terms
            if len(term) >= 4
            and term not in stop_terms
            and term not in subject_terms
            and term not in pain_terms
        ]
    )


def _has_voice_complaint_evidence(
    *,
    title: str,
    body: str,
    signal_text: str,
    query_family:Optional[ str] = None,
) -> bool:
    evidence_terms = list(_VOICE_COMPLAINT_EVIDENCE_TERMS)
    if str(query_family or "").strip().lower() == "comparison_complaint_discovery":
        evidence_terms.extend(_VOICE_COMPARE_EVIDENCE_TERMS)
    if _collect_hits(texts=[title, body, signal_text], terms=evidence_terms):
        return True
    signal_tokens = [token for token in signal_text.split() if token]
    return bool(signal_tokens)


def _source_quality(
    *,
    mode: str,
    subreddit: str,
    title: str,
    body: str,
    config: RetrievalPrecisionConfig,
) -> str:
    subreddit_text = str(subreddit or "").replace("r/", "").lower()
    title_text = str(title or "").lower()
    body_text = str(body or "").lower()
    if any(term in subreddit_text for term in config.suspicious_subreddit_terms):
        return "suspicious"
    if any(term in title_text for term in config.suspicious_title_terms):
        return "suspicious"
    if any(term in body_text for term in config.suspicious_body_terms):
        return "suspicious"
    trusted_terms = config.trusted_subreddit_terms.get(str(mode or "").lower(), [])
    if any(term in subreddit_text for term in trusted_terms):
        return "trusted"
    return "unknown"


def score_retrieval_candidate(
    *,
    mode: str,
    query_terms: list[str],
    subreddit: str,
    title: str,
    body: str,
    signals: list[str],
    positive_intent_terms:Optional[ list[str]] = None,
    forbidden_context_terms:Optional[ list[str]] = None,
    domain_terms:Optional[ list[str]] = None,
    strict_domain_terms:Optional[ list[str]] = None,
    strict_anchor_min_hits: int = 0,
    why_relevant:Optional[ str] = None,
    query_family:Optional[ str] = None,
    primary_friction:Optional[ str] = None,
    secondary_frictions:Optional[ list[str]] = None,
    request_query:Optional[ str] = None,
) -> RetrievalPrecisionDecision:
    config = load_retrieval_precision_config()
    signal_text = " ".join(signals)
    title_hits = _hit_terms(title, query_terms)
    body_hits = _hit_terms(body, query_terms)
    subreddit_hits = _hit_terms(subreddit, query_terms)
    signal_hits = _hit_terms(signal_text, query_terms)
    direct_hits = (
        len(title_hits) * 4
        + len(body_hits) * 2
        + len(subreddit_hits) * 2
        + len(signal_hits)
    )

    focus_terms = [term for term in query_terms if term not in config.generic_query_terms] or query_terms
    focus_hits = len(
        {
            *(_hit_terms(title, focus_terms)),
            *(_hit_terms(body, focus_terms)),
            *(_hit_terms(subreddit, focus_terms)),
            *(_hit_terms(" ".join(signals), focus_terms)),
        }
    )
    source_quality = _source_quality(
        mode=mode,
        subreddit=subreddit,
        title=title,
        body=body,
        config=config,
    )
    if source_quality == "suspicious" and config.suspicious_source_block:
        return RetrievalPrecisionDecision(
            source_quality=source_quality,
            blocked=True,
            keep=False,
            score=-100.0,
            direct_hits=direct_hits,
            focus_hits=focus_hits,
            reason="疑似广告/作业互助来源，已从候选证据中排除",
        )

    positive_hits = sorted(
        {
            *(_hit_terms(title, positive_intent_terms or [])),
            *(_hit_terms(body, positive_intent_terms or [])),
            *(_hit_terms(signal_text, positive_intent_terms or [])),
        }
    )
    forbidden_hits = sorted(
        {
            *(_hit_terms(subreddit, forbidden_context_terms or [])),
            *(_hit_terms(title, forbidden_context_terms or [])),
            *(_hit_terms(body, forbidden_context_terms or [])),
        }
    )
    visible_positive_hits = sorted(
        {
            *(_hit_terms(subreddit, positive_intent_terms or [])),
            *(_hit_terms(title, positive_intent_terms or [])),
        }
    )
    domain_hits = sorted(
        {
            *(_hit_terms(subreddit, domain_terms or [])),
            *(_hit_terms(title, domain_terms or [])),
            *(_hit_terms(body, domain_terms or [])),
            *(_hit_terms(signal_text, domain_terms or [])),
        }
    )
    visible_domain_hits = sorted(
        {
            *(_hit_terms(subreddit, domain_terms or [])),
            *(_hit_terms(title, domain_terms or [])),
        }
    )
    strict_hits = sorted(
        {
            *(_hit_terms(subreddit, strict_domain_terms or [])),
            *(_hit_terms(title, strict_domain_terms or [])),
        }
    )
    extra_reason_fragments: list[str] = []
    missing_platform_conversion_anchor = False

    score = float(direct_hits)
    if source_quality == "trusted":
        score += config.trusted_source_boost
    else:
        score -= config.unknown_source_penalty
    score += float(len(positive_hits)) * 2.0
    score += float(len(domain_hits)) * 1.5
    if direct_hits <= 0 and "命中关键词" in str(why_relevant or ""):
        score -= 2.0
    rant_text = f"{title} {body} {signal_text}"
    if str(mode or "").lower() == "rant":
        if query_family == "generic_complaint_discovery" and _contains_any(rant_text, _RANT_GENERIC_COMPLAINT_TERMS):
            score += 2.0
        if query_family == "platform_conversion_friction":
            has_pre_purchase_signal = _contains_any(rant_text, _RANT_PRE_PURCHASE_CONVERSION_TERMS)
            has_post_purchase_signal = _contains_any(rant_text, _RANT_POST_PURCHASE_FRICTION_TERMS)
            has_loss_signal = _contains_any(rant_text, _RANT_BUY_REASON_TERMS)
            if _contains_any(rant_text, _RANT_BUY_REASON_TERMS) and _contains_any(rant_text, _RANT_PLATFORM_COMMERCE_TERMS):
                score += 2.5
            if _contains_any(rant_text, _RANT_REQUEST_HELP_TERMS):
                score -= 3.0
            if has_pre_purchase_signal:
                score += 2.0
            if has_post_purchase_signal and not has_pre_purchase_signal:
                score -= 2.5
            if not has_pre_purchase_signal and not has_loss_signal:
                missing_platform_conversion_anchor = True
        if primary_friction == "trust_gap" and _contains_any(rant_text, _RANT_TRUST_TERMS):
            score += 1.5
        if primary_friction == "weak_buy_reason" and _contains_any(rant_text, _RANT_BUY_REASON_TERMS):
            score += 1.5
        if primary_friction == "transaction_friction" and _contains_any(rant_text, _RANT_TRANSACTION_TERMS):
            score += 1.5
        if secondary_frictions and "trust_gap" in secondary_frictions and _contains_any(rant_text, _RANT_TRUST_TERMS):
            score += 0.5

    keep = True
    if forbidden_hits:
        keep = False
        score -= 4.0
    if str(mode or "").lower() == "opportunity" and focus_hits < config.required_focus_hits_for_opportunity:
        keep = False
    if str(mode or "").lower() == "opportunity" and positive_intent_terms and not positive_hits and direct_hits <= 0:
        keep = False
    if str(mode or "").lower() == "opportunity" and source_quality == "unknown":
        if not visible_domain_hits or not visible_positive_hits:
            keep = False
            score -= 3.0
    if strict_anchor_min_hits > 0 and strict_domain_terms and len(strict_hits) < strict_anchor_min_hits:
        keep = False
        score -= 4.0
    if (
        str(mode or "").lower() == "rant"
        and query_family == "platform_conversion_friction"
        and _contains_any(rant_text, _RANT_POST_PURCHASE_FRICTION_TERMS)
        and not _contains_any(rant_text, _RANT_PRE_PURCHASE_CONVERSION_TERMS)
    ):
        keep = False
        score -= 4.0
    if (
        str(mode or "").lower() == "rant"
        and query_family == "platform_conversion_friction"
        and missing_platform_conversion_anchor
    ):
        keep = False
        score -= 4.0
        extra_reason_fragments.append("缺少转化问题锚点")
    if str(mode or "").lower() == "rant":
        normalized_family = str(query_family or "").strip().lower()
        is_voice_family = normalized_family in {
            "generic_complaint_discovery",
            "support_breakdown",
            "specific_issue",
            "comparison_complaint_discovery",
        }
        if is_voice_family:
            subject_terms = _subject_anchor_terms(
                query_terms=query_terms,
                domain_terms=domain_terms or [],
                strict_domain_terms=strict_domain_terms or [],
            )
            subject_hits = _collect_hits(
                texts=[subreddit, title, body],
                terms=subject_terms,
            )
            if subject_terms and not subject_hits:
                keep = False
                score -= 4.0
                extra_reason_fragments.append("缺少主题锚点")

            pain_terms = _pain_anchor_terms(
                query_terms=query_terms,
                positive_intent_terms=positive_intent_terms or [],
            )
            pain_hits = _collect_hits(
                texts=[title, body, signal_text],
                terms=pain_terms,
            )
            specific_issue_symptom_terms = (
                _specific_issue_symptom_terms(
                    query_terms=query_terms,
                    subject_terms=subject_terms,
                    pain_terms=pain_terms,
                    positive_intent_terms=positive_intent_terms or [],
                )
                if normalized_family == "specific_issue"
                else []
            )
            specific_issue_symptom_hits = _collect_hits(
                texts=[title, body, signal_text],
                terms=specific_issue_symptom_terms,
            )
            has_voice_evidence = _has_voice_complaint_evidence(
                title=title,
                body=body,
                signal_text=signal_text,
                query_family=normalized_family,
            )
            requires_explicit_pain_anchor = normalized_family == "generic_complaint_discovery"
            requires_voice_anchor = normalized_family in {"support_breakdown", "specific_issue"}
            if pain_terms and not pain_hits and (
                requires_explicit_pain_anchor
                or (requires_voice_anchor and not has_voice_evidence)
            ):
                specific_issue_symptom_fallback = (
                    normalized_family == "specific_issue"
                    and bool(subject_hits)
                    and bool(specific_issue_symptom_hits)
                )
                if specific_issue_symptom_fallback:
                    score -= 1.0
                    extra_reason_fragments.append("缺少通用抱怨词，已按症状锚点保留")
                else:
                    keep = False
                    score -= 3.0
                    extra_reason_fragments.append("缺少抱怨锚点")

            has_comparison_intent = _has_comparison_intent(
                request_query=request_query,
                query_terms=query_terms,
            )
            compare_requested = (
                normalized_family == "comparison_complaint_discovery"
                or has_comparison_intent
            )
            if compare_requested and len(subject_terms) >= 2:
                has_compare_cue = _contains_any(
                    f"{title} {body} {signal_text}",
                    list(_RANT_COMPARISON_HINTS),
                )
                requested_compare_entities = _requested_compare_entities(
                    query_terms=query_terms,
                    domain_terms=domain_terms or [],
                    strict_domain_terms=strict_domain_terms or [],
                )
                compare_entity_hits = _collect_hits(
                    texts=[subreddit, title, body],
                    terms=requested_compare_entities,
                )
                explicit_compare_entities = _extract_explicit_compare_entities(
                    f"{title} {body} {signal_text}"
                )
                foreign_compare_entities = [
                    term
                    for term in explicit_compare_entities
                    if term not in requested_compare_entities
                ]
                if normalized_family == "comparison_complaint_discovery":
                    if foreign_compare_entities and compare_entity_hits:
                        keep = False
                        score -= 5.0
                        extra_reason_fragments.append("错误比较对象")
                    elif not compare_entity_hits:
                        keep = False
                        score -= 4.0
                        extra_reason_fragments.append("缺少比较对象锚点")
                    elif not (len(compare_entity_hits) >= 2 or has_voice_evidence or has_compare_cue):
                        score -= 2.0
                        extra_reason_fragments.append("比较题单边命中，已降权保留")
                elif len(subject_hits) < 2:
                    keep = False
                    score -= 4.0
                    extra_reason_fragments.append("缺少比较对象锚点")

    matched_terms = sorted({*title_hits, *body_hits, *subreddit_hits, *signal_hits})
    if matched_terms:
        reason = f"直接命中: {', '.join(matched_terms[:3])}"
    else:
        reason = "未形成足够的直接命中"
    if positive_hits:
        reason = f"{reason}；意图命中: {', '.join(positive_hits[:2])}"
    if domain_hits:
        reason = f"{reason}；领域命中: {', '.join(domain_hits[:2])}"
    if forbidden_hits:
        reason = f"{reason}；错误语境: {', '.join(forbidden_hits[:2])}"
    if str(mode or "").lower() == "opportunity" and source_quality == "unknown" and (
        not visible_domain_hits or not visible_positive_hits
    ):
        reason = f"{reason}；未知社区缺少明确产品语境"
    if strict_anchor_min_hits > 0 and strict_domain_terms and len(strict_hits) < strict_anchor_min_hits:
        reason = f"{reason}；缺少严格问题域锚点"
    if (
        str(mode or "").lower() == "rant"
        and query_family == "platform_conversion_friction"
        and _contains_any(rant_text, _RANT_POST_PURCHASE_FRICTION_TERMS)
        and not _contains_any(rant_text, _RANT_PRE_PURCHASE_CONVERSION_TERMS)
    ):
        reason = f"{reason}；偏成交后履约/诈骗噪音"
    if source_quality == "trusted":
        reason = f"{reason}；社区语境匹配"
    elif source_quality == "unknown":
        reason = f"{reason}；社区语境待验证"
    if extra_reason_fragments:
        reason = f"{reason}；{'；'.join(extra_reason_fragments)}"

    return RetrievalPrecisionDecision(
        source_quality=source_quality,
        blocked=False,
        keep=keep,
        score=score,
        direct_hits=direct_hits,
        focus_hits=focus_hits,
        reason=reason,
    )


__all__ = [
    "RetrievalPrecisionDecision",
    "RetrievalPrecisionConfig",
    "load_retrieval_precision_config",
    "score_retrieval_candidate",
]
