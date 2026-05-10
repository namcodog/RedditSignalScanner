from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_mini_surface_v1.yaml"


def _as_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"hotpost_mini_surface_v1.yaml invalid {name}")
    return value


def _required_int(raw: dict[str, Any], key: str, *, name: str) -> int:
    if key not in raw:
        raise ValueError(f"hotpost_mini_surface_v1.yaml missing {name}.{key}")
    return int(raw[key])


def _required_str(raw: dict[str, Any], key: str, *, name: str) -> str:
    if key not in raw:
        raise ValueError(f"hotpost_mini_surface_v1.yaml missing {name}.{key}")
    value = str(raw[key]).strip()
    if not value:
        raise ValueError(f"hotpost_mini_surface_v1.yaml empty {name}.{key}")
    return value


@lru_cache(maxsize=1)
def load_hotpost_mini_surface_contract() -> dict[str, Any]:
    payload = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    contract = _as_mapping(payload, name="root")
    _as_mapping(contract.get("supplement_surface"), name="supplement_surface")
    return contract


def get_mini_supplement_surface_rules() -> dict[str, Any]:
    raw = _as_mapping(
        load_hotpost_mini_surface_contract()["supplement_surface"],
        name="supplement_surface",
    )
    name = "supplement_surface"
    return {
        "enabled": bool(raw.get("enabled", False)),
        "title": _required_str(raw, "title", name=name),
        "description": _required_str(raw, "description", name=name),
        "max_event_age_days": _required_int(raw, "max_event_age_days", name=name),
        "max_cards": _required_int(raw, "max_cards", name=name),
        "initial_page_size": _required_int(raw, "initial_page_size", name=name),
        "max_page_size": _required_int(raw, "max_page_size", name=name),
    }


__all__ = [
    "get_mini_supplement_surface_rules",
    "load_hotpost_mini_surface_contract",
]
