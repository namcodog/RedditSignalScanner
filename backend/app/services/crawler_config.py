"""Loader for crawler.yml tiered strategy configuration.

This module centralises parsing of the Spec 009 crawler configuration so that
Celery tasks, schedulers and diagnostics all share a single interpretation of
the YAML file. It keeps the runtime defaults resilient: when a field is
missing or misconfigured, the loader falls back to sensible constants or
environment overrides instead of crashing at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

CONFIG_PATH_CANDIDATES = (
    Path("backend/config/crawler.yml"),
    Path("config/crawler.yml"),
)


def _load_yaml() -> Mapping[str, Any]:
    for candidate in CONFIG_PATH_CANDIDATES:
        if candidate.exists():
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            except Exception:
                return {}
            if isinstance(data, Mapping):
                return data
            return {}
    return {}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_duration_to_hours(value: Any, *, default: int) -> int:
    if isinstance(value, (int, float)):
        return max(1, int(value))
    if isinstance(value, str):
        text = value.strip().lower()
        if text.endswith("h"):
            return max(1, _to_int(text[:-1], default))
        if text.endswith("d"):
            return max(1, _to_int(text[:-1], default) * 24)
    return default


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_base_seconds: int
    backoff_factor: float
    backoff_max_seconds: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, default: "RetryPolicy") -> "RetryPolicy":
        if not isinstance(data, Mapping):
            return default
        return cls(
            max_retries=_to_int(data.get("max_retries"), default.max_retries),
            backoff_base_seconds=_to_int(data.get("backoff_base_seconds"), default.backoff_base_seconds),
            backoff_factor=_to_float(data.get("backoff_factor"), default.backoff_factor),
            backoff_max_seconds=_to_int(data.get("backoff_max_seconds"), default.backoff_max_seconds),
        )


@dataclass(frozen=True)
class TierFallback:
    widen_time_filter_to: str | None = None
    relax_sort_mix: Dict[str, float] | None = None
    allow_unfiltered_on_exhausted: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "TierFallback":
        if not isinstance(data, Mapping):
            return cls()
        widen = data.get("widen_time_filter_to")
        relax = data.get("relax_sort_mix")
        relax_map: Dict[str, float] | None = None
        if isinstance(relax, Mapping):
            relax_map = {}
            for key, value in relax.items():
                if isinstance(key, str):
                    relax_map[key] = max(0.0, _to_float(value, 0.0))
        return cls(
            widen_time_filter_to=widen if isinstance(widen, str) and widen else None,
            relax_sort_mix=relax_map,
            allow_unfiltered_on_exhausted=bool(data.get("allow_unfiltered_on_exhausted", False)),
        )


@dataclass(frozen=True)
class TierSettings:
    name: str
    match_aliases: frozenset[str]
    re_crawl_frequency_hours: int
    time_filter: str
    sort_mix: Dict[str, float]
    post_limit: int
    retry: RetryPolicy
    hot_cache_ttl_hours: int
    fallback: TierFallback

    def pick_sort(self, *, default_sort: str) -> str:
        if not self.sort_mix:
            return default_sort
        # Deterministic choice: pick the highest-weighted sort, break ties alphabetically.
        return max(self.sort_mix.items(), key=lambda item: (item[1], item[0]))[0]

    def matches(self, tier: str) -> bool:
        return tier.strip().lower() in self.match_aliases


@dataclass(frozen=True)
class GlobalSettings:
    concurrency: int
    scheduler_batch_size: int
    max_db_concurrency: int
    timeout_seconds: int
    rate_limit_per_minute: int
    hot_cache_ttl_hours: int
    watermark_enabled: bool
    watermark_grace_hours: int
    retry: RetryPolicy


@dataclass(frozen=True)
class CrawlerConfig:
    version: int
    global_settings: GlobalSettings
    tiers: tuple[TierSettings, ...] = field(default_factory=tuple)

    def resolve_tier(self, tier: str) -> TierSettings | None:
        tier_norm = tier.strip().lower()
        for settings in self.tiers:
            if settings.matches(tier_norm):
                return settings
        return None


_DEFAULT_RETRY = RetryPolicy(
    max_retries=2,
    backoff_base_seconds=300,
    backoff_factor=2.0,
    backoff_max_seconds=3600,
)


def _normalise_aliases(name: str, aliases: Iterable[str]) -> frozenset[str]:
    base = {name.strip().lower()}
    for alias in aliases:
        if isinstance(alias, str) and alias.strip():
            base.add(alias.strip().lower())
    # Ensure canonical tier names are always matched
    name_lc = name.strip().lower()
    if name_lc in {"t1", "tier1"}:
        base.update({"tier1", "t1", "high", "gold", "seed"})
    elif name_lc in {"t2", "tier2"}:
        base.update({"tier2", "t2", "medium", "silver"})
    elif name_lc in {"t3", "tier3"}:
        base.update({"tier3", "t3", "low"})
    return frozenset(base)


def load_crawler_config() -> CrawlerConfig:
    raw = _load_yaml()
    version = _to_int(raw.get("version"), 1)
    global_raw = raw.get("global", {})
    global_retry = RetryPolicy.from_mapping(
        global_raw.get("retry"), default=_DEFAULT_RETRY
    )
    global_settings = GlobalSettings(
        concurrency=_to_int(global_raw.get("concurrency"), 4),
        scheduler_batch_size=_to_int(global_raw.get("scheduler_batch_size"), 12),
        max_db_concurrency=_to_int(global_raw.get("max_db_concurrency"), 2),
        timeout_seconds=_to_int(global_raw.get("timeout_seconds"), 20),
        rate_limit_per_minute=_to_int(global_raw.get("rate_limit_per_minute"), 60),
        hot_cache_ttl_hours=_to_int(global_raw.get("hot_cache_ttl_hours"), 24),
        watermark_enabled=bool(global_raw.get("watermark_enabled", True)),
        watermark_grace_hours=_to_int(global_raw.get("watermark_grace_hours"), 4),
        retry=global_retry,
    )

    tier_settings: list[TierSettings] = []
    for entry in raw.get("tiers", []) or []:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", "")) or "tier"
        aliases = entry.get("match_tiers", []) or []
        aliases = aliases if isinstance(aliases, Iterable) else []
        retry = RetryPolicy.from_mapping(entry.get("retry"), default=global_retry)
        sort_mix_raw = entry.get("sort_mix") or {}
        sort_mix: Dict[str, float] = {}
        if isinstance(sort_mix_raw, Mapping):
            for key, value in sort_mix_raw.items():
                if isinstance(key, str):
                    sort_mix[key.strip().lower()] = max(0.0, _to_float(value, 0.0))
        tier_settings.append(
            TierSettings(
                name=name,
                match_aliases=_normalise_aliases(name, aliases),
                re_crawl_frequency_hours=_parse_duration_to_hours(
                    entry.get("re_crawl_frequency"), default=24
                ),
                time_filter=str(entry.get("time_filter") or "month"),
                sort_mix=sort_mix,
                post_limit=_to_int(entry.get("post_limit"), 60),
                retry=retry,
                hot_cache_ttl_hours=_to_int(
                    entry.get("hot_cache_ttl_hours"),
                    global_settings.hot_cache_ttl_hours,
                ),
                fallback=TierFallback.from_mapping(entry.get("fallback")),
            )
        )

    return CrawlerConfig(
        version=version,
        global_settings=global_settings,
        tiers=tuple(tier_settings),
    )


_CONFIG_CACHE: CrawlerConfig | None = None


def get_crawler_config(reload: bool = False) -> CrawlerConfig:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None or reload:
        _CONFIG_CACHE = load_crawler_config()
    return _CONFIG_CACHE


__all__ = ["CrawlerConfig", "TierSettings", "GlobalSettings", "get_crawler_config"]

