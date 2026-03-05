from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any
from collections.abc import Mapping, Sequence

from app.services.analysis.topic_profiles import TopicProfile


@dataclass(frozen=True, slots=True)
class FactsV2QualityGateConfig:
    # Topic / relevance
    min_on_topic_ratio: float = 0.6
    max_sample_size: int = 50

    # Comments (optional gate; default off unless configured)
    min_sample_comments: int = 0

    # Completeness
    min_good_pains: int = 2
    pain_min_mentions: int = 10
    pain_min_unique_authors: int = 5
    pain_min_evidence: int = 1

    min_good_brands: int = 2
    brand_min_mentions: int = 10
    brand_min_unique_authors: int = 5
    brand_min_evidence: int = 3

    min_solutions: int = 5

    # Consistency
    range_mismatch_tolerance: float = 0.2  # 20%


@dataclass(frozen=True, slots=True)
class FactsV2QualityResult:
    passed: bool
    tier: str
    flags: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)


def _apply_profile_overrides(
    cfg: FactsV2QualityGateConfig, profile: TopicProfile | None
) -> FactsV2QualityGateConfig:
    if not profile:
        return cfg
    updates: dict[str, Any] = {}
    if profile.pain_min_mentions is not None and profile.pain_min_mentions > 0:
        updates["pain_min_mentions"] = profile.pain_min_mentions
    if profile.pain_min_unique_authors is not None and profile.pain_min_unique_authors > 0:
        updates["pain_min_unique_authors"] = profile.pain_min_unique_authors
    if profile.brand_min_mentions is not None and profile.brand_min_mentions > 0:
        updates["brand_min_mentions"] = profile.brand_min_mentions
    if profile.brand_min_unique_authors is not None and profile.brand_min_unique_authors > 0:
        updates["brand_min_unique_authors"] = profile.brand_min_unique_authors
    if profile.min_solutions is not None and profile.min_solutions >= 0:
        updates["min_solutions"] = profile.min_solutions
    if profile.min_sample_comments is not None and profile.min_sample_comments >= 0:
        updates["min_sample_comments"] = profile.min_sample_comments
    if not updates:
        return cfg
    return replace(cfg, **updates)


def quality_check_facts_v2(
    facts_v2: Mapping[str, object],
    *,
    profile: TopicProfile | None,
    config: FactsV2QualityGateConfig | None = None,
    skip_topic_check: bool = False,
) -> FactsV2QualityResult:
    cfg = _apply_profile_overrides(config or FactsV2QualityGateConfig(), profile)

    flags: list[str] = []
    metrics: dict[str, Any] = {}

    # 1) Topic match check (sample texts)
    meta = _as_dict(facts_v2.get("meta"))
    if profile is not None:
        required_terms = [t.lower() for t in (profile.required_entities_any or []) if t]
        soft_terms = [t.lower() for t in (profile.soft_required_entities_any or []) if t]
        include_src = [*(profile.include_keywords_any or []), *(profile.context_keywords_any or [])]
        include_terms = [t.lower() for t in include_src if t]
        exclude_terms = [t.lower() for t in (profile.exclude_keywords_any or []) if t]
        topic_terms_source = "profile"
    else:
        required_terms = []
        soft_terms = []
        include_terms = _extract_fallback_include_terms(meta)
        exclude_terms = []
        topic_terms_source = "meta" if include_terms else "none"

    sample_texts: list[str] = []
    for p in _as_list_of_dict(facts_v2.get("sample_posts_db")):
        text = _get_text(p, keys=("title", "text", "body"))
        if text:
            sample_texts.append(text)
    for c in _as_list_of_dict(facts_v2.get("sample_comments_db")):
        text = _get_text(c, keys=("text", "body"))
        if text:
            sample_texts.append(text)

    if skip_topic_check:
        metrics["topic_check_skipped"] = True
        metrics["on_topic_ratio"] = 1.0
        metrics["sample_checked"] = min(len(sample_texts), cfg.max_sample_size)
        metrics["topic_terms_source"] = topic_terms_source
        metrics["topic_terms_count"] = len(required_terms) + len(soft_terms) + len(include_terms)
    elif not (required_terms or soft_terms or include_terms):
        # 没有 profile 且 meta 里也提取不到可用英文关键词时：跳过 topic check，
        # 避免“全中文 topic”被硬判为跑偏。
        metrics["topic_check_skipped"] = True
        metrics["on_topic_ratio"] = 1.0
        metrics["sample_checked"] = min(len(sample_texts), cfg.max_sample_size)
        metrics["topic_terms_source"] = topic_terms_source
        metrics["topic_terms_count"] = 0
    elif sample_texts:
        sample = sample_texts[: cfg.max_sample_size]
        on_topic = 0
        for raw in sample:
            t = raw.lower()
            if any(x in t for x in exclude_terms):
                continue
            if any(x in t for x in required_terms) or any(x in t for x in soft_terms) or any(
                x in t for x in include_terms
            ):
                on_topic += 1
        ratio = on_topic / max(1, len(sample))
        metrics["on_topic_ratio"] = round(ratio, 3)
        metrics["sample_checked"] = len(sample)
        metrics["topic_terms_source"] = topic_terms_source
        metrics["topic_terms_count"] = len(required_terms) + len(soft_terms) + len(include_terms)
        if ratio < cfg.min_on_topic_ratio:
            flags.append("topic_mismatch")
    else:
        metrics["on_topic_ratio"] = 0.0
        metrics["sample_checked"] = 0
        metrics["topic_terms_source"] = topic_terms_source
        metrics["topic_terms_count"] = len(required_terms) + len(soft_terms) + len(include_terms)
        flags.append("topic_mismatch")

    # 2) Completeness checks
    business_signals = _as_dict(facts_v2.get("business_signals"))
    pains = _as_list_of_dict(business_signals.get("high_value_pains"))
    good_pains = 0
    for p in pains:
        title = _get_str(p, "title")
        metrics_node = _as_dict(p.get("metrics"))
        mentions = _get_int(metrics_node, "mentions")
        authors = _get_int(metrics_node, "unique_authors")
        evidence = _as_list_any(p.get("evidence_quote_ids"))
        if (
            title
            and mentions >= cfg.pain_min_mentions
            and authors >= cfg.pain_min_unique_authors
            and len(evidence) >= cfg.pain_min_evidence
        ):
            good_pains += 1
    metrics["good_pains"] = good_pains
    if good_pains < cfg.min_good_pains:
        flags.append("pains_low")

    brand_pain = _as_list_of_dict(business_signals.get("brand_pain"))
    good_brands = 0
    for b in brand_pain:
        mentions = _get_int(b, "mentions")
        authors = _get_int(b, "unique_authors")
        evidence = _as_list_any(b.get("evidence_quote_ids"))
        if (
            mentions >= cfg.brand_min_mentions
            and authors >= cfg.brand_min_unique_authors
            and len(evidence) >= cfg.brand_min_evidence
        ):
            good_brands += 1
    metrics["good_brands"] = good_brands
    if good_brands < cfg.min_good_brands:
        flags.append("brand_pain_low")

    solutions = _as_list_of_dict(business_signals.get("solutions"))
    metrics["solutions"] = len(solutions)
    if len(solutions) < cfg.min_solutions:
        flags.append("solutions_low")

    # 3) source_range vs aggregates consistency
    data_lineage = _as_dict(facts_v2.get("data_lineage"))
    source_range = _as_dict(data_lineage.get("source_range"))
    sr_posts = _get_int(source_range, "posts")
    sr_comments = _get_int(source_range, "comments")
    aggregates = _as_dict(facts_v2.get("aggregates"))
    communities = _as_list_of_dict(aggregates.get("communities"))
    agg_posts = sum(_get_int(c, "posts") for c in communities)
    agg_comments = sum(_get_int(c, "comments") for c in communities)
    metrics["source_posts"] = sr_posts
    metrics["source_comments"] = sr_comments
    metrics["agg_posts"] = agg_posts
    metrics["agg_comments"] = agg_comments
    metrics["min_sample_comments"] = cfg.min_sample_comments

    # 3.1) Comments consumption diagnostics (Contract C / P0.5)
    counts_db = _as_dict(data_lineage.get("counts_db"))
    db_comments_total = _get_int(counts_db, "comments_total")
    db_comments_eligible = _get_int(counts_db, "comments_eligible")
    metrics["db_comments_total"] = db_comments_total
    metrics["db_comments_eligible"] = db_comments_eligible
    pipeline_status = _get_str(data_lineage, "comments_pipeline_status")
    if pipeline_status:
        metrics["comments_pipeline_status"] = pipeline_status
    if db_comments_total > 0 and sr_comments <= 0:
        flags.append("comments_not_used")

    if cfg.min_sample_comments > 0 and sr_comments < cfg.min_sample_comments:
        flags.append("comments_low")

    if _mismatch_ratio(sr_posts, agg_posts) > cfg.range_mismatch_tolerance or _mismatch_ratio(
        sr_comments, agg_comments
    ) > cfg.range_mismatch_tolerance:
        flags.append("range_mismatch")

    # 4) Coverage status (DONE_12M / DONE_CAPPED / NEEDS ...)
    coverage = _as_dict(data_lineage.get("coverage"))
    raw_counts = _as_dict(coverage.get("status_counts"))
    status_counts: dict[str, int] = {}
    for key, value in raw_counts.items():
        if not isinstance(key, str):
            continue
        status_counts[key] = int(value or 0)

    coverage_total = sum(status_counts.values())
    metrics["coverage_status_counts"] = status_counts
    metrics["coverage_total"] = coverage_total
    metrics["coverage_months_min"] = _get_int(coverage, "coverage_months_min")
    metrics["coverage_months_avg"] = float(coverage.get("coverage_months_avg") or 0)
    metrics["coverage_months_max"] = _get_int(coverage, "coverage_months_max")
    metrics["coverage_capped_count"] = int(coverage.get("capped_count") or 0)

    coverage_tier = "unknown"
    if coverage_total > 0:
        done_12m = status_counts.get("DONE_12M", 0)
        done_capped = status_counts.get("DONE_CAPPED", 0)
        needs = status_counts.get("NEEDS", 0)
        running = status_counts.get("RUNNING", 0)
        error = status_counts.get("ERROR", 0)
        if done_12m == coverage_total and done_capped == 0:
            coverage_tier = "full"
        elif done_12m + done_capped == coverage_total and done_capped > 0:
            coverage_tier = "capped"
        elif needs or running or error:
            coverage_tier = "partial"
        else:
            coverage_tier = "partial"
    metrics["coverage_tier"] = coverage_tier
    if coverage_tier == "capped":
        flags.append("coverage_capped")
    elif coverage_tier == "partial":
        flags.append("coverage_partial")

    tier = _determine_report_tier(flags, metrics, cfg)
    passed = tier != "X_blocked"
    return FactsV2QualityResult(passed=passed, tier=tier, flags=flags, metrics=metrics)


def _determine_report_tier(
    flags: Sequence[str],
    metrics: Mapping[str, Any],
    cfg: FactsV2QualityGateConfig,
) -> str:
    # Hard blockers: topic mismatch or internal inconsistency
    if "topic_mismatch" in flags or "range_mismatch" in flags:
        return "X_blocked"
    # 如果明确要求评论样本，但评论为 0/不足：最多只给勘探版，避免“假装有结论”
    if "comments_low" in flags:
        return "C_scouting"
    # 评论库里有但本次没吃到：必须显式标红；若 topic 明确要求评论，则按勘探版处理。
    if "comments_not_used" in flags and cfg.min_sample_comments > 0:
        return "C_scouting"

    good_pains = int(metrics.get("good_pains") or 0)
    good_brands = int(metrics.get("good_brands") or 0)
    solutions = int(metrics.get("solutions") or 0)

    if (
        good_pains >= cfg.min_good_pains
        and good_brands >= cfg.min_good_brands
        and solutions >= cfg.min_solutions
    ):
        return "A_full"
    if good_pains >= 1:
        return "B_trimmed"
    return "C_scouting"


def _mismatch_ratio(expected: int, actual: int) -> float:
    if expected <= 0:
        return 0.0 if actual <= 0 else 1.0
    return abs(actual - expected) / expected


def _as_list_of_dict(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    out: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(item)
    return out


def _as_list_any(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _as_dict(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _get_str(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _get_int(row: Mapping[str, object], key: str) -> int:
    value = row.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _get_text(row: Mapping[str, object], *, keys: Sequence[str]) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


_FALLBACK_TOKEN_RE = re.compile(r"[a-z0-9]{3,}", flags=re.IGNORECASE)
_FALLBACK_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "your",
    "you",
    "are",
    "this",
    "that",
    "tool",
    "tools",
    "report",
    "reports",
    "analysis",
    "insight",
    "insights",
    "community",
    "communities",
}


def _extract_fallback_include_terms(meta: Mapping[str, object]) -> list[str]:
    """
    当 topic_profile 缺失时，从 meta 文本里提取“可用英文关键词”，用于 topic mismatch 的兜底拦截。
    规则：只取 [a-z0-9]{3,} 的 token（避开纯中文/碎片），并过滤一小撮通用词。
    """

    candidates: list[str] = []
    for key in ("product_description", "topic", "topic_name"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value)
    if not candidates:
        return []

    seen: set[str] = set()
    out: list[str] = []
    for raw in candidates:
        for match in _FALLBACK_TOKEN_RE.finditer(raw):
            token = match.group(0).lower()
            if not token or token.isdigit():
                continue
            if token in _FALLBACK_STOPWORDS:
                continue
            if token in seen:
                continue
            seen.add(token)
            out.append(token)
    return out
