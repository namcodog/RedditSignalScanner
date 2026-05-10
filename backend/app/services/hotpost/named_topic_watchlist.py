from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast, get_args

import yaml

from app.schemas.hotpost_signal import SourceScopeId
from app.schemas.hotpost_source_scopes import TimeFilter
from app.services.hotpost.hotpost_supply_contract import get_supply_scope, get_topic_pack_contract


@dataclass(frozen=True, slots=True)
class NamedTopicWatch:
    topic_id: str
    scope_id: SourceScopeId
    topic_pack_id: str
    queries: tuple[str, ...]
    subreddits: tuple[str, ...]
    topic_cluster_ids: tuple[str, ...] = ()
    time_filter: str = "week"
    candidate_cap: int = 4


_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_named_topic_watchlists.yaml"
_VALID_SCOPE_IDS = {str(item) for item in get_args(SourceScopeId)}
_VALID_TIME_FILTERS = {str(item) for item in get_args(TimeFilter)}


def resolve_named_topic_watchlist(topic_ids: list[str] | None = None, *, preset: str | None = None) -> list[NamedTopicWatch]:
    registry = load_named_topic_registry()
    presets = _load_presets()
    resolved_ids = list(topic_ids or [])
    resolved_preset = preset.strip() if preset else None
    if resolved_preset:
        if resolved_preset not in presets:
            raise KeyError(f"Unknown named-topic preset: {resolved_preset}")
        resolved_ids = [*resolved_ids, *presets[resolved_preset]]
    deduped_ids = list(dict.fromkeys(_normalize_topic_id(item, registry=registry) for item in resolved_ids))
    if not deduped_ids:
        return []
    return [registry[item] for item in deduped_ids]


def load_named_topic_registry() -> dict[str, NamedTopicWatch]:
    return dict(_load_registry())


def list_named_topic_presets() -> tuple[str, ...]:
    return tuple(_load_presets().keys())


def get_default_named_topic_preset() -> str:
    payload = _load_yaml()
    defaults = _as_mapping(payload.get("defaults"), name="defaults")
    preset = str(defaults.get("preset") or "").strip()
    if not preset:
        raise ValueError("hotpost_named_topic_watchlists.yaml missing defaults.preset")
    if preset not in _load_presets():
        raise ValueError(f"hotpost_named_topic_watchlists.yaml invalid defaults.preset: {preset}")
    return preset


@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, Any]:
    payload = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return _as_mapping(payload, name="root")


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, NamedTopicWatch]:
    payload = _load_yaml()
    raw_topics = _as_mapping(payload.get("topics"), name="topics")
    registry: dict[str, NamedTopicWatch] = {}
    for raw_topic_id, raw_topic in raw_topics.items():
        topic_id = _normalize_topic_id(str(raw_topic_id), registry=registry, allow_unknown=True)
        topic = _as_mapping(raw_topic, name=f"topics.{topic_id}")
        scope_id = _required_str(topic, "scope_id", name=f"topics.{topic_id}")
        _validate_scope_id(scope_id, name=f"topics.{topic_id}")
        topic_pack_id = _required_str(topic, "topic_pack_id", name=f"topics.{topic_id}")
        _validate_topic_pack(scope_id, topic_pack_id, name=f"topics.{topic_id}")
        topic_cluster_ids = _optional_str_list(topic, "topic_cluster_ids")
        _validate_topic_clusters(scope_id, topic_cluster_ids, name=f"topics.{topic_id}")
        time_filter = str(topic.get("time_filter") or "week").strip().lower()
        _validate_time_filter(time_filter, name=f"topics.{topic_id}")
        registry[topic_id] = NamedTopicWatch(
            topic_id=topic_id,
            scope_id=cast(SourceScopeId, scope_id),
            topic_pack_id=topic_pack_id,
            topic_cluster_ids=tuple(topic_cluster_ids),
            queries=tuple(_required_str_list(topic, "queries", name=f"topics.{topic_id}")),
            subreddits=tuple(_required_str_list(topic, "subreddits", name=f"topics.{topic_id}")),
            time_filter=time_filter,
            candidate_cap=max(1, int(topic.get("candidate_cap") or 4)),
        )
    if not registry:
        raise ValueError("hotpost_named_topic_watchlists.yaml missing topics")
    return registry


@lru_cache(maxsize=1)
def _load_presets() -> dict[str, tuple[str, ...]]:
    payload = _load_yaml()
    raw_presets = _as_mapping(payload.get("presets"), name="presets")
    registry = _load_registry()
    presets: dict[str, tuple[str, ...]] = {}
    for raw_preset_id, raw_topic_ids in raw_presets.items():
        preset_id = str(raw_preset_id).strip()
        if not preset_id:
            raise ValueError("hotpost_named_topic_watchlists.yaml invalid presets key")
        if not isinstance(raw_topic_ids, list) or not raw_topic_ids:
            raise ValueError(f"hotpost_named_topic_watchlists.yaml missing presets.{preset_id}")
        normalized_ids = tuple(_normalize_topic_id(str(item), registry=registry) for item in raw_topic_ids)
        presets[preset_id] = tuple(dict.fromkeys(normalized_ids))
    if not presets:
        raise ValueError("hotpost_named_topic_watchlists.yaml missing presets")
    return presets


def _normalize_topic_id(value: str, *, registry: dict[str, NamedTopicWatch], allow_unknown: bool = False) -> str:
    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    if normalized or allow_unknown:
        if allow_unknown:
            return normalized
        if normalized in registry:
            return normalized
    raise KeyError(f"Unknown named topic: {value}")


def _as_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"hotpost_named_topic_watchlists.yaml invalid {name}")
    return value


def _required_str(raw: dict[str, Any], key: str, *, name: str) -> str:
    value = str(raw.get(key) or "").strip()
    if not value:
        raise ValueError(f"hotpost_named_topic_watchlists.yaml missing {name}.{key}")
    return value


def _required_str_list(raw: dict[str, Any], key: str, *, name: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"hotpost_named_topic_watchlists.yaml missing {name}.{key}")
    resolved = [str(item).strip().replace("r/", "") for item in value if str(item).strip()]
    if not resolved:
        raise ValueError(f"hotpost_named_topic_watchlists.yaml missing {name}.{key}")
    return list(dict.fromkeys(resolved))


def _optional_str_list(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _validate_scope_id(scope_id: str, *, name: str) -> None:
    if scope_id not in _VALID_SCOPE_IDS:
        raise ValueError(f"hotpost_named_topic_watchlists.yaml invalid {name}.scope_id: {scope_id}")


def _validate_time_filter(time_filter: str, *, name: str) -> None:
    if time_filter not in _VALID_TIME_FILTERS:
        raise ValueError(f"hotpost_named_topic_watchlists.yaml invalid {name}.time_filter: {time_filter}")


def _validate_topic_pack(scope_id: str, topic_pack_id: str, *, name: str) -> None:
    try:
        get_topic_pack_contract(cast(SourceScopeId, scope_id), topic_pack_id)
    except KeyError as exc:
        raise ValueError(
            f"hotpost_named_topic_watchlists.yaml invalid {name}.topic_pack_id: {scope_id}/{topic_pack_id}"
        ) from exc


def _validate_topic_clusters(scope_id: str, topic_cluster_ids: list[str], *, name: str) -> None:
    if not topic_cluster_ids:
        return
    scope = get_supply_scope(cast(SourceScopeId, scope_id))
    valid_clusters = {str(item) for item in dict(scope.get("topic_clusters") or {}).keys()}
    invalid_clusters = [cluster_id for cluster_id in topic_cluster_ids if cluster_id not in valid_clusters]
    if invalid_clusters:
        raise ValueError(
            f"hotpost_named_topic_watchlists.yaml invalid {name}.topic_cluster_ids: {', '.join(invalid_clusters)}"
        )


__all__ = [
    "NamedTopicWatch",
    "get_default_named_topic_preset",
    "list_named_topic_presets",
    "load_named_topic_registry",
    "resolve_named_topic_watchlist",
]
