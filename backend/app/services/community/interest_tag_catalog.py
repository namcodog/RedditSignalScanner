from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "community_interest_tags.json"
)


@dataclass(frozen=True)
class InterestTagDefinition:
    tag_id: str
    display_name: str
    short_description: str
    group: str
    source_refs: tuple[str, ...]
    source_ref_match: bool
    category_keys: tuple[str, ...]
    keyword_keys: tuple[str, ...]
    semantic_keys: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationPolicy:
    generic_hotspot_keys: tuple[str, ...]
    generic_cap_ratio: float
    status_bonus: dict[str, float]
    score_weights: dict[str, float]
    reason_templates: dict[str, str]
    evidence_summary_templates: dict[str, str]
    activity_labels: dict[str, str]
    role_labels: dict[str, str]
    audit_rules: dict[str, dict[str, str]]


@dataclass(frozen=True)
class InterestTagCatalog:
    tags: tuple[InterestTagDefinition, ...]
    policy: RecommendationPolicy

    def definition_for(self, tag_id: str) -> InterestTagDefinition:
        for definition in self.tags:
            if definition.tag_id == tag_id:
                return definition
        raise ValueError(f"interest tag definition not found: {tag_id}")


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    items: list[str] = []
    for index, item in enumerate(value):
        items.append(_string(item, f"{field}[{index}]"))
    return tuple(items)


def _float(value: object, field: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _float_mapping(value: object, field: str) -> dict[str, float]:
    raw = _mapping(value, field)
    return {str(key): _float(item, f"{field}.{key}") for key, item in raw.items()}


def _string_mapping(value: object, field: str) -> dict[str, str]:
    raw = _mapping(value, field)
    return {str(key): _string(item, f"{field}.{key}") for key, item in raw.items()}


def _nested_string_mapping(value: object, field: str) -> dict[str, dict[str, str]]:
    raw = _mapping(value, field)
    return {
        str(key): _string_mapping(item, f"{field}.{key}")
        for key, item in raw.items()
    }


def _load_tag_definition(value: object, index: int) -> InterestTagDefinition:
    raw = _mapping(value, f"tags[{index}]")
    match = _mapping(raw.get("match"), f"tags[{index}].match")
    source_refs = _string_tuple(raw.get("source_refs"), f"tags[{index}].source_refs")
    if not source_refs:
        raise ValueError(f"tags[{index}].source_refs must not be empty")
    return InterestTagDefinition(
        tag_id=_string(raw.get("id"), f"tags[{index}].id"),
        display_name=_string(raw.get("display_name"), f"tags[{index}].display_name"),
        short_description=_string(
            raw.get("short_description"),
            f"tags[{index}].short_description",
        ),
        group=_string(raw.get("group"), f"tags[{index}].group"),
        source_refs=source_refs,
        source_ref_match=_bool(raw.get("source_ref_match", False), f"tags[{index}].source_ref_match"),
        category_keys=_string_tuple(match.get("categories", []), f"tags[{index}].match.categories"),
        keyword_keys=_string_tuple(match.get("keywords", []), f"tags[{index}].match.keywords"),
        semantic_keys=_string_tuple(
            match.get("semantic_terms", []),
            f"tags[{index}].match.semantic_terms",
        ),
    )


def _load_policy(value: object) -> RecommendationPolicy:
    raw = _mapping(value, "policy")
    score = _mapping(raw.get("score"), "policy.score")
    status_bonus = _float_mapping(score.get("status_bonus"), "policy.score.status_bonus")
    score_weights = {
        key: _float(score.get(key), f"policy.score.{key}")
        for key in score
        if key != "status_bonus"
    }
    return RecommendationPolicy(
        generic_hotspot_keys=_string_tuple(
            raw.get("generic_hotspot_keys"),
            "policy.generic_hotspot_keys",
        ),
        generic_cap_ratio=_float(raw.get("generic_cap_ratio"), "policy.generic_cap_ratio"),
        status_bonus=status_bonus,
        score_weights=score_weights,
        reason_templates=_string_mapping(
            raw.get("reason_templates"),
            "policy.reason_templates",
        ),
        evidence_summary_templates=_string_mapping(
            raw.get("evidence_summary_templates"),
            "policy.evidence_summary_templates",
        ),
        activity_labels=_string_mapping(
            raw.get("activity_labels"),
            "policy.activity_labels",
        ),
        role_labels=_string_mapping(raw.get("role_labels"), "policy.role_labels"),
        audit_rules=_nested_string_mapping(raw.get("audit_rules"), "policy.audit_rules"),
    )


def _validate_contract(payload: dict[str, Any], tags: tuple[InterestTagDefinition, ...]) -> None:
    contract = payload.get("contract")
    if contract is None:
        return
    raw = _mapping(contract, "contract")
    expected_count = raw.get("tag_count")
    if isinstance(expected_count, int) and expected_count != len(tags):
        raise ValueError("contract.tag_count must match tags length")


def load_interest_tag_catalog(path: Path | None = None) -> InterestTagCatalog:
    catalog_path = path or DEFAULT_CATALOG_PATH
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    raw = _mapping(payload, "catalog")
    tags_raw = raw.get("tags")
    if not isinstance(tags_raw, list):
        raise ValueError("tags must be a list")
    tags = tuple(_load_tag_definition(item, index) for index, item in enumerate(tags_raw))
    if not tags:
        raise ValueError("tags must not be empty")
    _validate_contract(raw, tags)
    return InterestTagCatalog(tags=tags, policy=_load_policy(raw.get("policy")))


__all__ = [
    "InterestTagCatalog",
    "InterestTagDefinition",
    "RecommendationPolicy",
    "load_interest_tag_catalog",
]
