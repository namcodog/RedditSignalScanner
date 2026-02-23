from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class HotpostLexicon:
    rant_signals: dict[str, list[str]]
    opportunity_signals: dict[str, list[str]]
    discovery_signals: dict[str, list[str]]
    intent_label: dict[str, list[str]]
    pain_categories: dict[str, list[str]]


def _normalize_terms(terms: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in terms:
        if raw is None:
            continue
        term = " ".join(str(raw).strip().lower().split())
        if not term or term in seen:
            continue
        seen.add(term)
        cleaned.append(term)
    return cleaned


def _normalize_group(payload: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, terms in payload.items():
        normalized[key] = _normalize_terms(terms)
    return normalized


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Hotpost keywords file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def load_hotpost_keywords(*, config_path: Path | None = None) -> HotpostLexicon:
    base_dir = Path(__file__).resolve().parents[3]
    default_path = base_dir / "config" / "boom_post_keywords.yaml"
    path = config_path or default_path
    payload = _load_yaml(path)

    rant = _normalize_group(payload.get("rant_signals", {}) or {})
    opportunity = _normalize_group(payload.get("opportunity_signals", {}) or {})
    discovery = _normalize_group(payload.get("discovery_signals", {}) or {})
    intent = _normalize_group(payload.get("intent_label", {}) or {})
    pains = _normalize_group(payload.get("pain_categories", {}) or {})

    return HotpostLexicon(
        rant_signals=rant,
        opportunity_signals=opportunity,
        discovery_signals=discovery,
        intent_label=intent,
        pain_categories=pains,
    )


@lru_cache
def load_default_hotpost_keywords() -> HotpostLexicon:
    return load_hotpost_keywords()


__all__ = ["HotpostLexicon", "load_hotpost_keywords", "load_default_hotpost_keywords"]
