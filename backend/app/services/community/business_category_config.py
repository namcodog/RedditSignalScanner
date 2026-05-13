from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_BUSINESS_CATEGORY_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "community_business_categories.json"
)


@dataclass(frozen=True)
class BusinessCategoryDefinition:
    key: str
    display_name: str
    description: str


@dataclass(frozen=True)
class BusinessCategoryConfig:
    categories: tuple[BusinessCategoryDefinition, ...]
    aliases: dict[str, str]
    role_categories: dict[str, str]
    scope_categories: dict[str, str]
    community_key_categories: dict[str, str]
    default_category: str


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_mapping(value: object, field: str) -> dict[str, str]:
    raw = _mapping(value or {}, field)
    return {str(key): _string(item, f"{field}.{key}") for key, item in raw.items()}


def _load_category(value: object, index: int) -> BusinessCategoryDefinition:
    raw = _mapping(value, f"categories[{index}]")
    return BusinessCategoryDefinition(
        key=_string(raw.get("key"), f"categories[{index}].key"),
        display_name=_string(raw.get("display_name"), f"categories[{index}].display_name"),
        description=_string(raw.get("description"), f"categories[{index}].description"),
    )


def _load_config(path: Path) -> BusinessCategoryConfig:
    raw = _mapping(json.loads(path.read_text(encoding="utf-8")), "business_categories")
    categories_raw = raw.get("categories")
    if not isinstance(categories_raw, list) or not categories_raw:
        raise ValueError("categories must be a non-empty list")
    inference = _mapping(raw.get("phase2_inference"), "phase2_inference")
    return BusinessCategoryConfig(
        categories=tuple(_load_category(item, index) for index, item in enumerate(categories_raw)),
        aliases=_string_mapping(raw.get("aliases"), "aliases"),
        role_categories=_string_mapping(inference.get("role_categories"), "phase2_inference.role_categories"),
        scope_categories=_string_mapping(inference.get("scope_categories"), "phase2_inference.scope_categories"),
        community_key_categories=_string_mapping(
            inference.get("community_key_categories"),
            "phase2_inference.community_key_categories",
        ),
        default_category=_string(inference.get("default_category"), "phase2_inference.default_category"),
    )


@lru_cache(maxsize=1)
def load_business_category_config(
    path: Path = DEFAULT_BUSINESS_CATEGORY_CONFIG_PATH,
) -> BusinessCategoryConfig:
    return _load_config(path)


def phase2_category_for(
    *,
    key: str,
    role: str,
    scopes: Iterable[str],
    config: BusinessCategoryConfig | None = None,
) -> str:
    active = config or load_business_category_config()
    if role in active.role_categories:
        return active.role_categories[role]
    for scope in scopes:
        if scope in active.scope_categories:
            return active.scope_categories[scope]
    return active.community_key_categories.get(key, active.default_category)
