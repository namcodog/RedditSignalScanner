from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


DictionaryType = dict[str, list[str]]

_CANONICAL_CATEGORIES = {"brands", "features", "pain_points", "channels", "logistics", "risks"}
_CATEGORY_ALIASES = {
    "channels": "channels",
    "channel": "channels",
    "marketplaces": "channels",
    "platforms": "channels",
    "markets": "channels",
    "metrics": "features",
    "use_cases": "features",
    "tooling": "features",
    "topics": "features",
    "models": "brands",
    "assets": "brands",
    "institutions": "brands",
    "indicators": "features",
    "risks": "risks",
    "risk": "risks",
    "hazards": "risks",
    "threats": "risks",
    "logistic": "logistics",
    "shipping": "logistics",
    "fulfillment": "logistics",
    "delivery": "logistics",
}


def _load_folder_dictionary(folder: Path) -> DictionaryType:
    """Load category->entities from a folder of yml files.

    - Each YAML file should contain a mapping like {category: [entities...]}
    - Categories from multiple files are merged (deduplicated, order-insensitive)
    """
    mapping: dict[str, set[str]] = {}
    if not folder.exists() or not folder.is_dir():
        return {}
    for yml in sorted(folder.glob("*.yml")):
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, Mapping):
            continue
        for cat, items in data.items():
            if not isinstance(items, Iterable):
                continue
            canonical = _CATEGORY_ALIASES.get(str(cat).lower(), str(cat))
            if canonical.lower() not in _CANONICAL_CATEGORIES:
                continue
            bucket = mapping.setdefault(str(canonical), set())
            for it in items:
                if isinstance(it, str) and it.strip():
                    bucket.add(it.strip())
    # normalise to list
    return {k: sorted(v) for k, v in mapping.items()}


def _compile_patterns(dictionary: DictionaryType) -> dict[str, list[tuple[str, re.Pattern]]]:
    compiled: dict[str, list[tuple[str, re.Pattern]]] = {}
    for cat, items in dictionary.items():
        arr: list[tuple[str, re.Pattern]] = []
        for token in items:
            escaped = re.escape(token)
            if re.search(r"[A-Za-z]", token):
                pat = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
            else:
                pat = re.compile(escaped, re.IGNORECASE)
            arr.append((token, pat))
        compiled[cat] = arr
    return compiled


@dataclass
class EntityHit:
    name: str
    category: str
    mentions: int


class EntityPipeline:
    """Folder-based entity recognition pipeline.

    This complements the lightweight EntityMatcher by supporting multiple
    dictionaries under `backend/config/entity_dictionary/*.yml` and provides
    a summarisation API compatible with the existing report payload.
    """

    def __init__(self, *, folder: str | Path | None = None) -> None:
        root = Path(folder) if folder is not None else Path(__file__).resolve().parents[3] / "config" / "entity_dictionary"
        self._dictionary: DictionaryType = _load_folder_dictionary(root)
        self._patterns = _compile_patterns(self._dictionary)

    def match_text(self, text: str | None) -> dict[str, list[str]]:
        if not text:
            return {cat: [] for cat in self._dictionary}
        hits: dict[str, set[str]] = {cat: set() for cat in self._dictionary}
        for raw_cat, patterns in self._patterns.items():
            canonical = _CATEGORY_ALIASES.get(raw_cat.lower(), raw_cat)
            if canonical.lower() not in _CANONICAL_CATEGORIES:
                continue
            for token, pat in patterns:
                if pat.search(text):
                    hits[canonical].add(token)
        return {cat: sorted(list(vals)) for cat, vals in hits.items()}

    def _consume(self, value: Any) -> dict[str, int]:
        counts: dict[str, int] = {}
        def _add(tokens: Iterable[str]) -> None:
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
        def _walk(v: Any) -> None:
            if isinstance(v, str):
                for cat, items in self.match_text(v).items():
                    _add([f"{cat}:::{name}" for name in items])
            elif isinstance(v, Mapping):
                for vv in v.values():
                    _walk(vv)
            elif isinstance(v, Iterable) and not isinstance(v, (bytes, bytearray)):
                for vv in v:
                    _walk(vv)
        _walk(value)
        return counts

    def summarize(self, insights: Mapping[str, Any], *, top_n: int = 5) -> dict[str, list[dict[str, int]]]:
        """Produce category-wise summary like EntityMatcher.summarize."""
        combined_counts: dict[str, int] = {}
        for key in ("pain_points", "competitors", "opportunities", "action_items"):
            for k, v in self._consume(insights.get(key)).items():
                combined_counts[k] = combined_counts.get(k, 0) + v
        # split back to categories
        by_cat: dict[str, dict[str, int]] = {cat: {} for cat in _CANONICAL_CATEGORIES}
        for packed, cnt in combined_counts.items():
            if ":::" not in packed:
                continue
            cat, name = packed.split(":::", 1)
            canonical = _CATEGORY_ALIASES.get(cat.lower(), cat)
            if canonical.lower() not in _CANONICAL_CATEGORIES:
                canonical = "features"
            bucket = by_cat.setdefault(canonical, {})
            bucket[name] = bucket.get(name, 0) + cnt
        # top-N
        result: dict[str, list[dict[str, int]]] = {}
        for cat, m in by_cat.items():
            items = sorted(m.items(), key=lambda x: x[1], reverse=True)[:top_n]
            result[cat] = [{"name": name, "mentions": count} for name, count in items]

        if all((not items) for items in result.values()):
            fallback = self._fallback_keywords(insights, top_n=top_n)
            if fallback:
                result["features"] = fallback
        return result

    @staticmethod
    def _fallback_keywords(insights: Mapping[str, Any], *, top_n: int) -> list[dict[str, int]]:
        payload_sections = []
        for section in ("pain_points", "competitors", "opportunities", "action_items"):
            value = insights.get(section)
            if value:
                payload_sections.append(value)

        counter: Counter[str] = Counter()

        def _scan(value: Any) -> None:
            if isinstance(value, str):
                for token in _extract_tokens(value):
                    counter[token] += 1
            elif isinstance(value, Mapping):
                for item in value.values():
                    _scan(item)
            elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
                for item in value:
                    _scan(item)

        for payload in payload_sections:
            _scan(payload)

        most_common = [item for item in counter.most_common(top_n) if item[1] > 0]
        return [{"name": name, "mentions": count} for name, count in most_common]


_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}")
_STOPWORDS = {
    "the",
    "and",
    "with",
    "that",
    "this",
    "from",
    "into",
    "have",
    "about",
    "people",
    "just",
    "your",
    "will",
    "need",
    "have",
    "been",
    "over",
    "into",
    "more",
    "less",
    "very",
    "also",
    "into",
    "like",
    "they",
    "them",
    "with",
    "want",
    "what",
    "that",
    "really",
    "because",
    "their",
}


def _extract_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _TOKEN_PATTERN.findall(text or ""):
        candidate = match.lower()
        if candidate in _STOPWORDS:
            continue
        tokens.append(candidate)
    return tokens


__all__ = ["EntityPipeline", "EntityHit"]
