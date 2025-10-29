from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml


class EntityMatcher:
    """Lightweight entity dictionary matcher for Phase 8 entity highlighting."""

    _DEFAULT_PATH = (
        Path(__file__).resolve().parents[3] / "config" / "entity_dictionary.yaml"
    )

    def __init__(self, *, config_path: str | Path | None = None) -> None:
        path = Path(config_path) if config_path is not None else self._DEFAULT_PATH
        if not path.exists():
            raise FileNotFoundError(f"Entity dictionary file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            raw_dict = yaml.safe_load(handle) or {}
        if not isinstance(raw_dict, Mapping):
            raise ValueError(
                "Entity dictionary must be a mapping of categories to entities."
            )

        self._dictionary: dict[str, tuple[str, ...]] = {}
        for category, entities in raw_dict.items():
            if not isinstance(entities, Iterable):
                continue
            normalized = tuple(
                str(entity).strip()
                for entity in entities
                if isinstance(entity, str) and entity.strip()
            )
            if normalized:
                self._dictionary[str(category)] = normalized

        # Precompile regex patterns for faster matching (case-insensitive, word-boundary safe for latin tokens)
        self._patterns: dict[str, tuple[tuple[str, re.Pattern], ...]] = {}
        for category, entities in self._dictionary.items():
            compiled: list[tuple[str, re.Pattern]] = []
            for entity in entities:
                token = re.escape(entity)
                # Allow partial matches for multi-word or non-latin words by falling back to simple search
                if re.search(r"[A-Za-z]", entity):
                    pattern = re.compile(rf"\b{token}\b", re.IGNORECASE)
                else:
                    pattern = re.compile(token, re.IGNORECASE)
                compiled.append((entity, pattern))
            self._patterns[category] = tuple(compiled)

    def match_text(self, text: str | None) -> dict[str, list[str]]:
        """Match dictionary entities against the provided text."""
        if not text:
            return {category: [] for category in self._dictionary}

        matches: dict[str, set[str]] = {
            category: set() for category in self._dictionary
        }
        for category, patterns in self._patterns.items():
            for entity, pattern in patterns:
                if pattern.search(text):
                    matches[category].add(entity)

        return {category: sorted(values) for category, values in matches.items()}

    def summarize(
        self, insights: Mapping[str, Any], *, top_n: int = 5
    ) -> dict[str, list[dict[str, int]]]:
        """
        Aggregate entity counts from structured insights output.

        Args:
            insights: Analysis insights payload containing pain_points / competitors / opportunities.
            top_n: Maximum number of entries per category.
        """
        counters: dict[str, Counter[str]] = {
            category: Counter() for category in self._dictionary
        }

        def _consume_text(value: Any) -> None:
            if isinstance(value, str):
                matches = self.match_text(value)
                for category, items in matches.items():
                    counters[category].update(items)
            elif isinstance(value, Mapping):
                for nested in value.values():
                    _consume_text(nested)
            elif isinstance(value, Iterable) and not isinstance(
                value, (bytes, bytearray)
            ):
                for item in value:
                    _consume_text(item)

        for key in ("pain_points", "competitors", "opportunities", "action_items"):
            _consume_text(insights.get(key))

        summary: dict[str, list[dict[str, int]]] = {}
        for category, counter in counters.items():
            most_common = counter.most_common(top_n)
            summary[category] = [
                {"name": name, "mentions": count} for name, count in most_common
            ]
        return summary


__all__ = ["EntityMatcher"]
