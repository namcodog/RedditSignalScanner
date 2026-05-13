from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, cast

CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
DEFAULT_GUARD_PATH = CONFIG_ROOT / "brand_match_guard.json"
CONTEXT_WINDOW = 40


@dataclass(frozen=True)
class BrandMatchGuard:
    guarded_statuses: frozenset[str]
    blocked_terms: frozenset[str]
    ambiguous_terms: frozenset[str]
    context_terms: frozenset[str]


def load_brand_match_guard(path: Path = DEFAULT_GUARD_PATH) -> BrandMatchGuard:
    payload = _load_json(path)
    return BrandMatchGuard(
        guarded_statuses=frozenset(_strings(payload.get("guarded_statuses"))),
        blocked_terms=frozenset(_normalized(_strings(payload.get("blocked_terms")))),
        ambiguous_terms=frozenset(
            _normalized(_strings(payload.get("ambiguous_terms")))
        ),
        context_terms=frozenset(_normalized(_strings(payload.get("context_terms")))),
    )


def is_brand_text_match_safe(
    canonical_name: str,
    review_status: str,
    source_text: str,
    guard: BrandMatchGuard,
) -> bool:
    if review_status not in guard.guarded_statuses:
        return True
    if not _contains_phrase(source_text, canonical_name):
        return False
    if _normalize(canonical_name) in guard.blocked_terms:
        return False
    if _normalize(canonical_name) not in guard.ambiguous_terms:
        return True
    return _has_case_match(source_text, canonical_name) or _has_context(
        source_text, canonical_name, guard.context_terms
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(_phrase_pattern(phrase), text, flags=re.IGNORECASE) is not None


def _has_case_match(text: str, phrase: str) -> bool:
    return re.search(_phrase_pattern(phrase), text) is not None


def _has_context(text: str, phrase: str, terms: frozenset[str]) -> bool:
    match = re.search(_phrase_pattern(phrase), text, flags=re.IGNORECASE)
    if match is None:
        return False
    start = max(0, match.start() - CONTEXT_WINDOW)
    end = min(len(text), match.end() + CONTEXT_WINDOW)
    window = text[start:end].lower()
    return any(re.search(_phrase_pattern(term), window) for term in terms)


def _phrase_pattern(value: str) -> str:
    words = [re.escape(item) for item in value.strip().split()]
    return r"\b" + r"\s+".join(words) + r"\b"


def _load_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def _strings(value: object) -> tuple[str, ...]:
    return (
        tuple(item for item in value if isinstance(item, str))
        if isinstance(value, list)
        else ()
    )


def _normalized(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_normalize(value) for value in values)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
