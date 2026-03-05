from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.utils.subreddit import normalize_subreddit_name


DEFAULT_COMMUNITY_ROLES_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "community_roles.yaml"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


@lru_cache(maxsize=8)
def load_community_role_map(path: Path = DEFAULT_COMMUNITY_ROLES_PATH) -> dict[str, str]:
    payload = _load_yaml(path)
    roles = payload.get("roles") or {}

    role_map: dict[str, str] = {}
    if not isinstance(roles, dict):
        return role_map

    for role_name, conf in roles.items():
        if not role_name:
            continue
        if not isinstance(conf, dict):
            continue
        communities = _as_list(conf.get("communities"))
        for community in communities:
            key = normalize_subreddit_name(str(community))
            if key:
                role_map[key] = str(role_name)
    return role_map


def communities_for_role(
    role: str, *, path: Path = DEFAULT_COMMUNITY_ROLES_PATH
) -> set[str]:
    role_key = (role or "").strip().lower()
    if not role_key:
        return set()

    role_map = load_community_role_map(path)
    return {
        subreddit
        for subreddit, mapped_role in role_map.items()
        if (mapped_role or "").strip().lower() == role_key
    }


__all__ = ["DEFAULT_COMMUNITY_ROLES_PATH", "load_community_role_map", "communities_for_role"]
