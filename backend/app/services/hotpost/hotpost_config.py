from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any, Iterable

import yaml


@dataclass(frozen=True)
class HotpostKeywordExtractionConfig:
    token_pattern: str
    min_length: int
    max_keywords: int
    stopwords: list[str]


@dataclass(frozen=True)
class HotpostQueryResolutionConfig:
    keyword_extraction: HotpostKeywordExtractionConfig
    planner: "HotpostQueryPlannerConfig"
    default_time_filters: dict[str, str]


@dataclass(frozen=True)
class HotpostQueryPlannerConfig:
    max_query_parts: int
    max_expanded_terms: int
    max_negative_terms: int
    noise_terms: list[str]
    strategy_by_mode: dict[str, str]
    intent_labels: dict[str, str]
    mode_terms: dict[str, list[str]]
    term_aliases: dict[str, list[str]]
    candidate_subreddits: dict[str, list[str]]
    positive_intent_terms: dict[str, list[str]]
    forbidden_context_terms: dict[str, list[str]]
    domain_terms: dict[str, list[str]]
    strict_domain_terms: dict[str, list[str]]
    strict_anchor_min_hits: dict[str, int]


@dataclass(frozen=True)
class HotpostTrendThresholds:
    explosive_score: int
    rising_score: int
    rising_comments: int


@dataclass(frozen=True)
class HotpostContractConfig:
    top_quotes_limit: int
    suggested_keywords_limit: int
    trending_topic_limit: int
    trend_thresholds: HotpostTrendThresholds


@dataclass(frozen=True)
class HotpostAutoRemediationConfig:
    enabled: bool
    max_rounds: int
    max_added_query_parts: int
    max_added_subreddits: int
    mode_terms: dict[str, list[str]]
    gap_terms: dict[str, list[str]]
    subreddit_hints: dict[str, list[str]]


@dataclass(frozen=True)
class HotpostLLMRoutingConfig:
    fast_model: str
    reasoning_model: str
    reasoning_enabled: bool
    reasoning_trigger_modes: list[str]
    reasoning_min_evidence: int
    reasoning_min_evidence_by_mode: dict[str, int]
    reasoning_trigger_on_gaps: bool


@dataclass(frozen=True)
class HotpostRedditGuardrailsConfig:
    initial_query_parts_limit: int
    initial_query_parts_limit_by_mode: dict[str, int]
    initial_subreddits_limit: int
    initial_subreddits_limit_by_mode: dict[str, int]
    remediation_query_parts_limit: int
    remediation_query_parts_limit_by_mode: dict[str, int]
    remediation_subreddits_limit: int
    remediation_subreddits_limit_by_mode: dict[str, int]
    search_request_timeout_seconds: float
    max_posts_per_subreddit: int
    max_comment_posts: int
    max_comment_posts_by_mode: dict[str, int]
    circuit_breaker_cooldown_seconds: int


@dataclass(frozen=True)
class HotpostEvidenceRankingConfig:
    relevance_weight: float
    quoteability_weight: float
    freshness_weight: float
    comments_weight: float
    signal_weight: float
    max_suggested_subreddits: int
    opportunity_hint_priority: bool


@dataclass(frozen=True)
class HotpostEvidencePackagingModeConfig:
    query_weight: float
    intent_weight: float
    domain_weight: float
    why_relevant_weight: float
    keep_focus_only: bool
    min_post_score: float
    min_comment_score: float


@dataclass(frozen=True)
class HotpostEvidencePackagingConfig:
    title_max_chars: int
    why_relevant_max_chars: int
    focus_terms_limit: int
    mode_rules: dict[str, HotpostEvidencePackagingModeConfig]


@dataclass(frozen=True)
class HotpostModeInsightsConfig:
    trending_explosive_hours: int
    trending_rising_days: int
    trending_sustained_days: int
    rant_high_severity_percentage: float
    rant_medium_severity_percentage: float
    opportunity_high_me_too_count: int
    opportunity_medium_me_too_count: int
    opportunity_high_wtp_bonus: float
    opportunity_medium_wtp_bonus: float
    opportunity_workaround_bonus: float


@dataclass(frozen=True)
class HotpostRuntimeConfig:
    query: HotpostQueryResolutionConfig
    contract: HotpostContractConfig
    remediation: HotpostAutoRemediationConfig
    llm: HotpostLLMRoutingConfig
    reddit: HotpostRedditGuardrailsConfig
    ranking: HotpostEvidenceRankingConfig
    packaging: HotpostEvidencePackagingConfig
    insights: HotpostModeInsightsConfig


def _normalize_terms(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in values:
        term = " ".join(str(raw or "").strip().lower().split())
        if not term or term in seen:
            continue
        seen.add(term)
        cleaned.append(term)
    return cleaned


def _normalize_term_map(payload: Optional[dict[str, Any]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, values in (payload or {}).items():
        normalized[str(key).strip().lower()] = _normalize_terms(values or [])
    return normalized


def _as_int(value: Any, *, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_float(value: Any, *, default: float, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_str(value: Any, *, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_int_map(payload: Optional[dict[str, Any]]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in (payload or {}).items():
        normalized[str(key).strip().lower()] = _as_int(value, default=0, minimum=0)
    return normalized


def _build_packaging_mode_config(
    payload: Optional[dict[str, Any]]
) -> HotpostEvidencePackagingModeConfig:
    data = dict(payload or {})
    return HotpostEvidencePackagingModeConfig(
        query_weight=_as_float(data.get("query_weight"), default=3.0),
        intent_weight=_as_float(data.get("intent_weight"), default=1.5),
        domain_weight=_as_float(data.get("domain_weight"), default=2.0),
        why_relevant_weight=_as_float(data.get("why_relevant_weight"), default=1.0),
        keep_focus_only=_as_bool(data.get("keep_focus_only"), default=False),
        min_post_score=_as_float(data.get("min_post_score"), default=0.0),
        min_comment_score=_as_float(data.get("min_comment_score"), default=0.0),
    )


def _env_or_value(key: str, value: Any) -> Any:
    env_value = os.getenv(key)
    if env_value is None:
        return value
    stripped = str(env_value).strip()
    if not stripped:
        return value
    return stripped


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Hotpost runtime config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        return {}
    return data


def load_hotpost_runtime_config(
    *, config_path: Optional[Path] = None
) -> HotpostRuntimeConfig:
    base_dir = Path(__file__).resolve().parents[3]
    path = config_path or (base_dir / "config" / "hotpost_quality.yaml")
    payload = _load_yaml(path)

    query_payload = dict(payload.get("query_resolution") or {})
    keyword_payload = dict(query_payload.get("keyword_extraction") or {})
    planner_payload = dict(query_payload.get("query_planner") or {})
    keyword_config = HotpostKeywordExtractionConfig(
        token_pattern=str(
            keyword_payload.get("token_pattern") or "[a-zA-Z][a-zA-Z0-9_\\-]{1,}"
        ),
        min_length=_as_int(keyword_payload.get("min_length"), default=3, minimum=1),
        max_keywords=_as_int(keyword_payload.get("max_keywords"), default=8, minimum=1),
        stopwords=_normalize_terms(keyword_payload.get("stopwords") or []),
    )
    planner_config = HotpostQueryPlannerConfig(
        max_query_parts=_as_int(
            planner_payload.get("max_query_parts"), default=3, minimum=1
        ),
        max_expanded_terms=_as_int(
            planner_payload.get("max_expanded_terms"), default=6, minimum=1
        ),
        max_negative_terms=_as_int(
            planner_payload.get("max_negative_terms"), default=6, minimum=0
        ),
        noise_terms=_normalize_terms(planner_payload.get("noise_terms") or []),
        strategy_by_mode={
            str(key).strip().lower(): _as_str(value, default="global-first")
            for key, value in dict(
                planner_payload.get("strategy_by_mode") or {}
            ).items()
        },
        intent_labels={
            str(key).strip().lower(): _as_str(value, default="discovery")
            for key, value in dict(planner_payload.get("intent_labels") or {}).items()
        },
        mode_terms=_normalize_term_map(planner_payload.get("mode_terms") or {}),
        term_aliases=_normalize_term_map(planner_payload.get("term_aliases") or {}),
        candidate_subreddits=_normalize_term_map(
            planner_payload.get("candidate_subreddits") or {}
        ),
        positive_intent_terms=_normalize_term_map(
            planner_payload.get("positive_intent_terms") or {}
        ),
        forbidden_context_terms=_normalize_term_map(
            planner_payload.get("forbidden_context_terms") or {}
        ),
        domain_terms=_normalize_term_map(planner_payload.get("domain_terms") or {}),
        strict_domain_terms=_normalize_term_map(
            planner_payload.get("strict_domain_terms") or {}
        ),
        strict_anchor_min_hits=_normalize_int_map(
            planner_payload.get("strict_anchor_min_hits") or {}
        ),
    )
    query_config = HotpostQueryResolutionConfig(
        keyword_extraction=keyword_config,
        planner=planner_config,
        default_time_filters={
            str(key).strip().lower(): _as_str(value, default="month")
            for key, value in dict(
                query_payload.get("default_time_filters") or {}
            ).items()
        },
    )

    contract_payload = dict(payload.get("quality_contract") or {})
    threshold_payload = dict(contract_payload.get("trend_thresholds") or {})
    trend_thresholds = HotpostTrendThresholds(
        explosive_score=_as_int(
            threshold_payload.get("explosive_score"), default=500, minimum=1
        ),
        rising_score=_as_int(
            threshold_payload.get("rising_score"), default=100, minimum=1
        ),
        rising_comments=_as_int(
            threshold_payload.get("rising_comments"), default=30, minimum=1
        ),
    )
    contract_config = HotpostContractConfig(
        top_quotes_limit=_as_int(
            contract_payload.get("top_quotes_limit"), default=3, minimum=1
        ),
        suggested_keywords_limit=_as_int(
            contract_payload.get("suggested_keywords_limit"),
            default=5,
            minimum=1,
        ),
        trending_topic_limit=_as_int(
            contract_payload.get("trending_topic_limit"), default=3, minimum=1
        ),
        trend_thresholds=trend_thresholds,
    )

    remediation_payload = dict(payload.get("auto_remediation") or {})
    remediation_config = HotpostAutoRemediationConfig(
        enabled=_as_bool(
            _env_or_value(
                "HOTPOST_REMEDIATION_ENABLED", remediation_payload.get("enabled")
            ),
            default=True,
        ),
        max_rounds=_as_int(
            _env_or_value(
                "HOTPOST_REMEDIATION_MAX_ROUNDS", remediation_payload.get("max_rounds")
            ),
            default=1,
            minimum=0,
        ),
        max_added_query_parts=_as_int(
            _env_or_value(
                "HOTPOST_REMEDIATION_MAX_ADDED_QUERY_PARTS",
                remediation_payload.get("max_added_query_parts"),
            ),
            default=2,
            minimum=0,
        ),
        max_added_subreddits=_as_int(
            _env_or_value(
                "HOTPOST_REMEDIATION_MAX_ADDED_SUBREDDITS",
                remediation_payload.get("max_added_subreddits"),
            ),
            default=3,
            minimum=0,
        ),
        mode_terms=_normalize_term_map(remediation_payload.get("mode_terms") or {}),
        gap_terms=_normalize_term_map(remediation_payload.get("gap_terms") or {}),
        subreddit_hints=_normalize_term_map(
            remediation_payload.get("subreddit_hints") or {}
        ),
    )
    llm_payload = dict(payload.get("llm_routing") or {})
    trigger_modes_value = _env_or_value(
        "HOTPOST_REASONING_TRIGGER_MODES",
        llm_payload.get("reasoning_trigger_modes"),
    )
    trigger_modes = (
        _normalize_terms(str(trigger_modes_value).split(","))
        if isinstance(trigger_modes_value, str)
        else _normalize_terms(trigger_modes_value or [])
    )
    llm_config = HotpostLLMRoutingConfig(
        fast_model=_as_str(
            _env_or_value("HOTPOST_FAST_MODEL", llm_payload.get("fast_model")),
            default="deepseek/deepseek-v4-flash",
        ),
        reasoning_model=_as_str(
            _env_or_value(
                "HOTPOST_REASONING_MODEL", llm_payload.get("reasoning_model")
            ),
            default="deepseek/deepseek-v4-pro",
        ),
        reasoning_enabled=_as_bool(
            _env_or_value(
                "HOTPOST_REASONING_ENABLED", llm_payload.get("reasoning_enabled")
            ),
            default=True,
        ),
        reasoning_trigger_modes=trigger_modes or ["opportunity"],
        reasoning_min_evidence=_as_int(
            _env_or_value(
                "HOTPOST_REASONING_MIN_EVIDENCE",
                llm_payload.get("reasoning_min_evidence"),
            ),
            default=10,
            minimum=0,
        ),
        reasoning_min_evidence_by_mode=_normalize_int_map(
            llm_payload.get("reasoning_min_evidence_by_mode") or {}
        ),
        reasoning_trigger_on_gaps=_as_bool(
            _env_or_value(
                "HOTPOST_REASONING_TRIGGER_ON_GAPS",
                llm_payload.get("reasoning_trigger_on_gaps"),
            ),
            default=True,
        ),
    )
    reddit_payload = dict(payload.get("reddit_guardrails") or {})
    reddit_config = HotpostRedditGuardrailsConfig(
        initial_query_parts_limit=_as_int(
            _env_or_value(
                "HOTPOST_INITIAL_QUERY_PARTS_LIMIT",
                reddit_payload.get("initial_query_parts_limit"),
            ),
            default=1,
            minimum=1,
        ),
        initial_query_parts_limit_by_mode=_normalize_int_map(
            reddit_payload.get("initial_query_parts_limit_by_mode") or {}
        ),
        initial_subreddits_limit=_as_int(
            _env_or_value(
                "HOTPOST_INITIAL_SUBREDDITS_LIMIT",
                reddit_payload.get("initial_subreddits_limit"),
            ),
            default=2,
            minimum=0,
        ),
        initial_subreddits_limit_by_mode=_normalize_int_map(
            reddit_payload.get("initial_subreddits_limit_by_mode") or {}
        ),
        remediation_query_parts_limit=_as_int(
            _env_or_value(
                "HOTPOST_REMEDIATION_QUERY_PARTS_LIMIT",
                reddit_payload.get("remediation_query_parts_limit"),
            ),
            default=1,
            minimum=1,
        ),
        remediation_query_parts_limit_by_mode=_normalize_int_map(
            reddit_payload.get("remediation_query_parts_limit_by_mode") or {}
        ),
        remediation_subreddits_limit=_as_int(
            _env_or_value(
                "HOTPOST_REMEDIATION_SUBREDDITS_LIMIT",
                reddit_payload.get("remediation_subreddits_limit"),
            ),
            default=2,
            minimum=0,
        ),
        remediation_subreddits_limit_by_mode=_normalize_int_map(
            reddit_payload.get("remediation_subreddits_limit_by_mode") or {}
        ),
        search_request_timeout_seconds=_as_float(
            _env_or_value(
                "HOTPOST_SEARCH_REQUEST_TIMEOUT_SECONDS",
                reddit_payload.get("search_request_timeout_seconds"),
            ),
            default=15.0,
            minimum=1.0,
        ),
        max_posts_per_subreddit=_as_int(
            _env_or_value(
                "HOTPOST_MAX_POSTS_PER_SUBREDDIT",
                reddit_payload.get("max_posts_per_subreddit"),
            ),
            default=40,
            minimum=1,
        ),
        max_comment_posts=_as_int(
            _env_or_value(
                "HOTPOST_MAX_COMMENT_POSTS",
                reddit_payload.get("max_comment_posts"),
            ),
            default=8,
            minimum=0,
        ),
        max_comment_posts_by_mode=_normalize_int_map(
            reddit_payload.get("max_comment_posts_by_mode") or {}
        ),
        circuit_breaker_cooldown_seconds=_as_int(
            _env_or_value(
                "HOTPOST_CIRCUIT_BREAKER_COOLDOWN_SECONDS",
                reddit_payload.get("circuit_breaker_cooldown_seconds"),
            ),
            default=90,
            minimum=1,
        ),
    )
    ranking_payload = dict(payload.get("evidence_ranking") or {})
    weights_payload = dict(ranking_payload.get("weights") or {})
    ranking_config = HotpostEvidenceRankingConfig(
        relevance_weight=_as_float(weights_payload.get("relevance"), default=4.0),
        quoteability_weight=_as_float(weights_payload.get("quoteability"), default=2.0),
        freshness_weight=_as_float(weights_payload.get("freshness"), default=1.5),
        comments_weight=_as_float(weights_payload.get("comments"), default=1.0),
        signal_weight=_as_float(weights_payload.get("signals"), default=1.0),
        max_suggested_subreddits=_as_int(
            ranking_payload.get("max_suggested_subreddits"),
            default=5,
            minimum=1,
        ),
        opportunity_hint_priority=_as_bool(
            ranking_payload.get("opportunity_hint_priority"),
            default=True,
        ),
    )
    packaging_payload = dict(payload.get("evidence_packaging") or {})
    packaging_modes = dict(packaging_payload.get("modes") or {})
    packaging_config = HotpostEvidencePackagingConfig(
        title_max_chars=_as_int(
            packaging_payload.get("title_max_chars"),
            default=140,
            minimum=40,
        ),
        why_relevant_max_chars=_as_int(
            packaging_payload.get("why_relevant_max_chars"),
            default=120,
            minimum=40,
        ),
        focus_terms_limit=_as_int(
            packaging_payload.get("focus_terms_limit"),
            default=4,
            minimum=1,
        ),
        mode_rules={
            str(key).strip().lower(): _build_packaging_mode_config(value)
            for key, value in packaging_modes.items()
        },
    )
    insights_payload = dict(payload.get("mode_insights") or {})
    trending_payload = dict(insights_payload.get("trending") or {})
    rant_payload = dict(insights_payload.get("rant") or {})
    opportunity_payload = dict(insights_payload.get("opportunity") or {})
    insights_config = HotpostModeInsightsConfig(
        trending_explosive_hours=_as_int(
            trending_payload.get("explosive_hours"),
            default=72,
            minimum=1,
        ),
        trending_rising_days=_as_int(
            trending_payload.get("rising_days"),
            default=7,
            minimum=1,
        ),
        trending_sustained_days=_as_int(
            trending_payload.get("sustained_days"),
            default=30,
            minimum=1,
        ),
        rant_high_severity_percentage=_as_float(
            rant_payload.get("high_severity_percentage"),
            default=0.35,
        ),
        rant_medium_severity_percentage=_as_float(
            rant_payload.get("medium_severity_percentage"),
            default=0.2,
        ),
        opportunity_high_me_too_count=_as_int(
            opportunity_payload.get("high_me_too_count"),
            default=5,
            minimum=1,
        ),
        opportunity_medium_me_too_count=_as_int(
            opportunity_payload.get("medium_me_too_count"),
            default=3,
            minimum=1,
        ),
        opportunity_high_wtp_bonus=_as_float(
            opportunity_payload.get("high_wtp_bonus"),
            default=2.0,
        ),
        opportunity_medium_wtp_bonus=_as_float(
            opportunity_payload.get("medium_wtp_bonus"),
            default=1.0,
        ),
        opportunity_workaround_bonus=_as_float(
            opportunity_payload.get("workaround_bonus"),
            default=1.5,
        ),
    )

    return HotpostRuntimeConfig(
        query=query_config,
        contract=contract_config,
        remediation=remediation_config,
        llm=llm_config,
        reddit=reddit_config,
        ranking=ranking_config,
        packaging=packaging_config,
        insights=insights_config,
    )


@lru_cache
def load_default_hotpost_runtime_config() -> HotpostRuntimeConfig:
    return load_hotpost_runtime_config()


__all__ = [
    "HotpostAutoRemediationConfig",
    "HotpostContractConfig",
    "HotpostEvidencePackagingConfig",
    "HotpostEvidencePackagingModeConfig",
    "HotpostEvidenceRankingConfig",
    "HotpostKeywordExtractionConfig",
    "HotpostLLMRoutingConfig",
    "HotpostModeInsightsConfig",
    "HotpostQueryResolutionConfig",
    "HotpostRuntimeConfig",
    "HotpostTrendThresholds",
    "load_default_hotpost_runtime_config",
    "load_hotpost_runtime_config",
]
