from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.schemas.hotpost_signal import SourceScopeId


_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_supply_discovery_v2.yaml"


def _as_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"hotpost_supply_discovery_v2.yaml invalid {name}")
    return value


def _required_int(raw: dict[str, Any], key: str, *, name: str) -> int:
    if key not in raw:
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return int(raw[key])


def _required_list(raw: dict[str, Any], key: str, *, name: str) -> list[Any]:
    if key not in raw or not isinstance(raw[key], list):
        raise ValueError(f"hotpost_supply_discovery_v2.yaml missing {name}.{key}")
    return list(raw[key])


@lru_cache(maxsize=1)
def load_hotpost_supply_contract() -> dict[str, Any]:
    payload = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    contract = _as_mapping(payload, name="root")
    _as_mapping(contract.get("global_rules"), name="global_rules")
    _as_mapping(contract.get("scopes"), name="scopes")
    return contract


def get_supply_scope(scope_id: SourceScopeId) -> dict[str, Any]:
    scopes = _as_mapping(load_hotpost_supply_contract()["scopes"], name="scopes")
    scope = scopes.get(scope_id)
    if scope is None:
        raise KeyError(f"Unknown hotpost supply scope: {scope_id}")
    return _as_mapping(scope, name=f"scope:{scope_id}")


def get_scope_topic_pack_contracts(scope_id: SourceScopeId) -> dict[str, dict[str, Any]]:
    scope = get_supply_scope(scope_id)
    topic_packs = _as_mapping(scope.get("topic_packs"), name=f"{scope_id}.topic_packs")
    return {pack_id: _as_mapping(raw, name=f"{scope_id}.{pack_id}") for pack_id, raw in topic_packs.items()}


def get_topic_pack_contract(scope_id: SourceScopeId, topic_pack_id: str) -> dict[str, Any]:
    packs = get_scope_topic_pack_contracts(scope_id)
    pack = packs.get(topic_pack_id)
    if pack is None:
        raise KeyError(f"Unknown hotpost topic pack: {scope_id}/{topic_pack_id}")
    return pack


def get_supply_global_rules() -> dict[str, Any]:
    return _as_mapping(load_hotpost_supply_contract()["global_rules"], name="global_rules")


def get_supply_collect_defaults() -> dict[str, int]:
    rules = get_supply_global_rules()
    raw = _as_mapping(rules.get("collect_defaults"), name="global_rules.collect_defaults")
    name = "global_rules.collect_defaults"
    return {
        "max_candidates_per_scope": _required_int(raw, "max_candidates_per_scope", name=name),
        "search_fetch_limit": _required_int(raw, "search_fetch_limit", name=name),
        "listing_fetch_limit": _required_int(raw, "listing_fetch_limit", name=name),
        "comments_fetch_limit": _required_int(raw, "comments_fetch_limit", name=name),
        "comment_request_timeout": _required_int(raw, "comment_request_timeout", name=name),
        "api_max_concurrency": _required_int(raw, "api_max_concurrency", name=name),
        "low_quota_remaining_threshold": _required_int(raw, "low_quota_remaining_threshold", name=name),
        "low_quota_cooldown_seconds": _required_int(raw, "low_quota_cooldown_seconds", name=name),
        "stop_comment_fetch_below_remaining": _required_int(raw, "stop_comment_fetch_below_remaining", name=name),
        "max_consecutive_rate_limit_errors": _required_int(raw, "max_consecutive_rate_limit_errors", name=name),
        "spec_batch_size": _required_int(raw, "spec_batch_size", name=name),
        "max_search_specs_per_scope": _required_int(raw, "max_search_specs_per_scope", name=name),
        "max_listing_specs_per_scope": _required_int(raw, "max_listing_specs_per_scope", name=name),
        "subreddit_candidate_cap": _required_int(raw, "subreddit_candidate_cap", name=name),
        "search_subreddit_limit": _required_int(raw, "search_subreddit_limit", name=name),
        "listing_subreddit_limit": _required_int(raw, "listing_subreddit_limit", name=name),
        "keywords_per_bucket": _required_int(raw, "keywords_per_bucket", name=name),
        "template_queries_per_segment": _required_int(raw, "template_queries_per_segment", name=name),
        "max_search_specs_per_segment": _required_int(raw, "max_search_specs_per_segment", name=name),
        "max_listing_specs_per_segment": _required_int(raw, "max_listing_specs_per_segment", name=name),
        "dry_cycle": _required_int(raw, "dry_cycle", name=name),
    }


def get_supply_collect_profile(mode: str = "harvest") -> dict[str, int]:
    defaults = get_supply_collect_defaults()
    rules = get_supply_global_rules()
    profiles = _as_mapping(rules.get("collect_profiles"), name="global_rules.collect_profiles")
    if mode not in profiles:
        raise KeyError(f"Unknown hotpost collect profile: {mode}")
    profile = _as_mapping(profiles[mode], name=f"global_rules.collect_profiles.{mode}")
    merged = dict(defaults)
    for key, value in profile.items():
        merged[str(key)] = int(value)
    return merged


def get_supply_experimental_collect_rules() -> dict[str, Any]:
    rules = get_supply_global_rules()
    raw = _as_mapping(rules.get("experimental_collect"), name="global_rules.experimental_collect")
    name = "global_rules.experimental_collect"
    return {
        "include_by_default": bool(raw.get("include_by_default", False)),
        "max_communities_per_scope": _required_int(raw, "max_communities_per_scope", name=name),
        "max_search_specs_per_cluster": _required_int(raw, "max_search_specs_per_cluster", name=name),
        "max_listing_specs_per_cluster": _required_int(raw, "max_listing_specs_per_cluster", name=name),
        "search_subreddit_limit": _required_int(raw, "search_subreddit_limit", name=name),
        "listing_subreddit_limit": _required_int(raw, "listing_subreddit_limit", name=name),
    }


def get_supply_operation_defaults() -> dict[str, int]:
    rules = get_supply_global_rules()
    raw = _as_mapping(rules.get("operation_defaults"), name="global_rules.operation_defaults")
    name = "global_rules.operation_defaults"
    return {
        "runs_per_day": _required_int(raw, "runs_per_day", name=name),
        "min_cards_per_run": _required_int(raw, "min_cards_per_run", name=name),
        "feed_initial_page_size": _required_int(raw, "feed_initial_page_size", name=name),
        "feed_max_page_size": _required_int(raw, "feed_max_page_size", name=name),
        "review_queue_limit": _required_int(raw, "review_queue_limit", name=name),
        "breakdown_materialize_limit": _required_int(raw, "breakdown_materialize_limit", name=name),
    }


def get_supply_hot_lane_rules() -> dict[str, Any]:
    rules = get_supply_global_rules()
    raw = _as_mapping(rules.get("hot_lane"), name="global_rules.hot_lane")
    name = "global_rules.hot_lane"
    return {
        "min_score": _required_int(raw, "min_score", name=name),
        "min_comments": _required_int(raw, "min_comments", name=name),
        "min_quote_count": _required_int(raw, "min_quote_count", name=name),
        "min_collective_comments": _required_int(raw, "min_collective_comments", name=name),
        "sustained_override_min_score": _required_int(raw, "sustained_override_min_score", name=name),
        "sustained_override_min_comments": _required_int(raw, "sustained_override_min_comments", name=name),
        "high_heat_override_score": _required_int(raw, "high_heat_override_score", name=name),
        "high_heat_override_comments": _required_int(raw, "high_heat_override_comments", name=name),
        "direct_question_markers": {str(item).lower() for item in _required_list(raw, "direct_question_markers", name=name)},
        "title_debate_terms": {str(item).lower() for item in _required_list(raw, "title_debate_terms", name=name)},
        "blocked_subreddits": [str(item).lower() for item in _required_list(raw, "blocked_subreddits", name=name)],
        "action_intents": {str(item) for item in _required_list(raw, "action_intents", name=name)},
        "reject_terms": {str(item).lower() for item in _required_list(raw, "reject_terms", name=name)},
        "practical_share_terms": {str(item).lower() for item in _required_list(raw, "practical_share_terms", name=name)},
        "debate_or_collective_terms": {str(item).lower() for item in _required_list(raw, "debate_or_collective_terms", name=name)},
        "collective_reporting_terms": {str(item).lower() for item in _required_list(raw, "collective_reporting_terms", name=name)},
        "platform_action_terms": {str(item).lower() for item in _required_list(raw, "platform_action_terms", name=name)},
    }


def get_supply_rolling_publish_mix() -> dict[str, Any]:
    rules = get_supply_global_rules()
    raw = _as_mapping(rules.get("rolling_publish_mix"), name="global_rules.rolling_publish_mix")
    lane_targets = _as_mapping(raw.get("lane_targets"), name="global_rules.rolling_publish_mix.lane_targets")
    scope_targets = _as_mapping(raw.get("scope_targets"), name="global_rules.rolling_publish_mix.scope_targets")
    return {
        "window_size": _required_int(raw, "window_size", name="global_rules.rolling_publish_mix"),
        "lane_targets": {str(key): int(value) for key, value in lane_targets.items()},
        "scope_targets": {str(key): int(value) for key, value in scope_targets.items()},
    }


def resolve_supply_lane_targets(target_total: int) -> dict[str, int]:
    rules = get_supply_rolling_publish_mix()
    configured = {str(key): int(value) for key, value in rules["lane_targets"].items()}
    return _resolve_scaled_targets(
        target_total,
        configured,
        tie_order=("signal", "hot", "breakdown"),
        overflow_prefers_smaller_targets=False,
    )


def _resolve_scaled_targets(
    target_total: int,
    configured: dict[str, int],
    *,
    tie_order: tuple[str, ...],
    overflow_prefers_smaller_targets: bool,
) -> dict[str, int]:
    total = sum(configured.values())
    if target_total <= 0:
        return {key: 0 for key in configured}
    if total == target_total:
        return dict(configured)
    if total <= 0:
        first = tie_order[0] if tie_order else next(iter(configured), "signal")
        return {key: (target_total if key == first else 0) for key in configured}

    keys = list(configured.keys())
    order_rank = {name: index for index, name in enumerate(tie_order)}
    raw_targets = {
        key: (target_total * float(configured[key]) / float(total))
        for key in keys
    }
    base = {key: int(raw_targets[key]) for key in keys}
    remainder = target_total - sum(base.values())
    if remainder == 0:
        return base

    ranked_keys = sorted(
        keys,
        key=lambda key: (
            -(raw_targets[key] - base[key]) if remainder > 0 else (raw_targets[key] - base[key]),
            configured[key] if overflow_prefers_smaller_targets else -configured[key],
            order_rank.get(key, len(order_rank)),
            key,
        ),
    )
    if remainder > 0:
        for key in ranked_keys[:remainder]:
            base[key] += 1
        return base

    for key in ranked_keys[: abs(remainder)]:
        if base[key] > 0:
            base[key] -= 1
    return base


__all__ = [
    "get_scope_topic_pack_contracts",
    "get_supply_collect_defaults",
    "get_supply_collect_profile",
    "get_supply_experimental_collect_rules",
    "get_supply_global_rules",
    "get_supply_hot_lane_rules",
    "get_supply_operation_defaults",
    "resolve_supply_lane_targets",
    "get_supply_rolling_publish_mix",
    "get_supply_scope",
    "get_topic_pack_contract",
    "load_hotpost_supply_contract",
]
