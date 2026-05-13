from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, cast

CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
DEFAULT_PROFILE_PATH = CONFIG_ROOT / "brand_consumer_profiles.json"


@dataclass(frozen=True)
class BrandConsumerProfile:
    profile_id: str
    review_statuses: tuple[str, ...]
    include_internal_fields: bool
    field_contract_version: str
    display_statuses: Mapping[str, str]
    exclude_risk_flags: bool = False


def load_brand_consumer_profile(
    profile_id: str = "consumer_safe",
    *,
    path: Path = DEFAULT_PROFILE_PATH,
) -> BrandConsumerProfile:
    payload = _load_json(path)
    profiles = _mapping(payload.get("profiles"))
    profile = _mapping(profiles.get(profile_id))
    if not profile:
        raise ValueError(f"Unknown brand consumer profile: {profile_id}")
    return BrandConsumerProfile(
        profile_id=profile_id,
        review_statuses=_strings(profile.get("review_statuses")),
        include_internal_fields=profile.get("include_internal_fields") is True,
        field_contract_version=_text(profile.get("field_contract_version")),
        display_statuses=_string_mapping(payload.get("display_statuses")),
        exclude_risk_flags=profile.get("exclude_risk_flags") is True,
    )


def _load_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, dict) else {}


def _string_mapping(value: object) -> dict[str, str]:
    mapping = _mapping(value)
    return {key: str(item) for key, item in mapping.items() if isinstance(key, str)}


def _strings(value: object) -> tuple[str, ...]:
    return (
        tuple(item for item in value if isinstance(item, str))
        if isinstance(value, list)
        else ()
    )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
