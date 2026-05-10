from __future__ import annotations

from pathlib import Path
from typing import Any, cast, get_args

import yaml

from app.schemas.hotpost_signal import SourceScopeId
from app.schemas.hotpost_source_scopes import TimeFilter
from app.services.hotpost.hotpost_supply_contract import get_supply_scope, get_topic_pack_contract
from app.services.hotpost.named_topic_candidate_collector import build_custom_named_topic_watch
from app.services.hotpost.named_topic_watchlist import NamedTopicWatch


_DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_card_supplement_profiles.yaml"
_VALID_SCOPE_IDS = {str(item) for item in get_args(SourceScopeId)}
_VALID_TIME_FILTERS = {str(item) for item in get_args(TimeFilter)}


def load_named_topic_watch_profile(
    profile_id: str,
    *,
    config_path: str | Path | None = None,
    time_filter_override: str | None = None,
) -> list[NamedTopicWatch]:
    payload = _load_yaml(Path(config_path) if config_path else _DEFAULT_PROFILE_PATH)
    profiles = _as_mapping(payload.get("profiles"), name="profiles")
    raw_profile = profiles.get(profile_id)
    if raw_profile is None:
        raise KeyError(f"Unknown named topic watch profile: {profile_id}")
    profile = _as_mapping(raw_profile, name=f"profiles.{profile_id}")
    raw_watches = profile.get("watches")
    if not isinstance(raw_watches, list) or not raw_watches:
        raise ValueError(f"hotpost_card_supplement_profiles.yaml missing profiles.{profile_id}.watches")

    watches: list[NamedTopicWatch] = []
    for index, raw_watch in enumerate(raw_watches):
        watch = _as_mapping(raw_watch, name=f"profiles.{profile_id}.watches[{index}]")
        watch_name = f"profiles.{profile_id}.watches[{index}]"
        scope_id = _required_str(watch, "scope_id", name=watch_name)
        _validate_scope_id(scope_id, name=watch_name)
        topic_pack_id = _required_str(watch, "topic_pack_id", name=watch_name)
        _validate_topic_pack(scope_id, topic_pack_id, name=watch_name)
        topic_cluster_ids = _optional_str_list(watch, "topic_cluster_ids")
        _validate_topic_clusters(scope_id, topic_cluster_ids, name=watch_name)
        resolved_time_filter = str(time_filter_override or watch.get("time_filter") or "week").strip().lower()
        _validate_time_filter(resolved_time_filter, name=watch_name)
        watches.append(
            build_custom_named_topic_watch(
                topic_id=_required_str(watch, "topic_id", name=watch_name),
                scope_id=scope_id,
                topic_pack_id=topic_pack_id,
                topic_cluster_ids=topic_cluster_ids,
                queries=_required_str_list(watch, "queries", name=watch_name),
                subreddits=_required_str_list(watch, "subreddits", name=watch_name),
                time_filter=resolved_time_filter,
                candidate_cap=max(1, int(watch.get("candidate_cap") or 4)),
            )
        )
    return watches


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _as_mapping(payload, name="root")


def _as_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"hotpost_card_supplement_profiles.yaml invalid {name}")
    return value


def _required_str(raw: dict[str, Any], key: str, *, name: str) -> str:
    value = str(raw.get(key) or "").strip()
    if not value:
        raise ValueError(f"hotpost_card_supplement_profiles.yaml missing {name}.{key}")
    return value


def _required_str_list(raw: dict[str, Any], key: str, *, name: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"hotpost_card_supplement_profiles.yaml missing {name}.{key}")
    resolved = [str(item).strip() for item in value if str(item).strip()]
    if not resolved:
        raise ValueError(f"hotpost_card_supplement_profiles.yaml missing {name}.{key}")
    return resolved


def _optional_str_list(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_scope_id(scope_id: str, *, name: str) -> None:
    if scope_id not in _VALID_SCOPE_IDS:
        raise ValueError(f"hotpost_card_supplement_profiles.yaml invalid {name}.scope_id: {scope_id}")


def _validate_time_filter(time_filter: str, *, name: str) -> None:
    if time_filter not in _VALID_TIME_FILTERS:
        raise ValueError(f"hotpost_card_supplement_profiles.yaml invalid {name}.time_filter: {time_filter}")


def _validate_topic_pack(scope_id: str, topic_pack_id: str, *, name: str) -> None:
    try:
        get_topic_pack_contract(cast(SourceScopeId, scope_id), topic_pack_id)
    except KeyError as exc:
        raise ValueError(
            f"hotpost_card_supplement_profiles.yaml invalid {name}.topic_pack_id: {scope_id}/{topic_pack_id}"
        ) from exc


def _validate_topic_clusters(scope_id: str, topic_cluster_ids: list[str], *, name: str) -> None:
    if not topic_cluster_ids:
        return
    scope = get_supply_scope(cast(SourceScopeId, scope_id))
    valid_clusters = {str(item) for item in dict(scope.get("topic_clusters") or {}).keys()}
    invalid_clusters = [cluster_id for cluster_id in topic_cluster_ids if cluster_id not in valid_clusters]
    if invalid_clusters:
        raise ValueError(
            f"hotpost_card_supplement_profiles.yaml invalid {name}.topic_cluster_ids: {', '.join(invalid_clusters)}"
        )


__all__ = ["load_named_topic_watch_profile"]
