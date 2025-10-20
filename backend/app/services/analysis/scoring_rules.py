"""Scoring rules loader for opportunity heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Sequence

import yaml


@dataclass(frozen=True)
class KeywordRule:
    keyword: str
    weight: float


@dataclass(frozen=True)
class NegationRule:
    pattern: str
    impact: float


@dataclass(frozen=True)
class ScoringRules:
    positive_keywords: Sequence[KeywordRule]
    negative_keywords: Sequence[KeywordRule]
    negation_patterns: Sequence[NegationRule]


class ScoringRulesLoader:
    """Load scoring configuration from YAML with lightweight caching."""

    def __init__(self, config_path: Path | None = None) -> None:
        base = Path(__file__).resolve()
        if config_path is None:
            resolved = None
            for parent in base.parents:
                candidate = parent / "config" / "scoring_rules.yaml"
                if candidate.exists():
                    resolved = candidate
                    break
            if resolved is None:
                resolved = Path.cwd() / "config" / "scoring_rules.yaml"
            self._path = resolved
        else:
            self._path = config_path
        self._cache: ScoringRules | None = None
        self._mtime: float | None = None
        self._lock = Lock()

    def load(self) -> ScoringRules:
        with self._lock:
            current_mtime = self._path.stat().st_mtime
            if self._cache is not None and current_mtime == self._mtime:
                return self._cache

            with self._path.open("r", encoding="utf-8") as fh:
                payload = yaml.safe_load(fh) or {}

            rules = ScoringRules(
                positive_keywords=self._parse_keyword_rules(
                    payload.get("positive_keywords", []), default_weight=0.1
                ),
                negative_keywords=self._parse_keyword_rules(
                    payload.get("negative_keywords", []), default_weight=-0.2
                ),
                negation_patterns=self._parse_negation_rules(
                    payload.get("negation_patterns", [])
                ),
            )

            self._cache = rules
            self._mtime = current_mtime
            return rules

    @staticmethod
    def _parse_keyword_rules(
        items: Iterable[object], *, default_weight: float
    ) -> List[KeywordRule]:
        rules: List[KeywordRule] = []
        for item in items:
            if isinstance(item, dict):
                keyword = str(item.get("keyword", "")).strip().lower()
                weight = item.get("weight", default_weight)
            else:
                keyword = str(item).strip().lower()
                weight = default_weight

            if not keyword:
                continue

            try:
                weight_value = float(weight)
            except (TypeError, ValueError):
                weight_value = default_weight

            rules.append(KeywordRule(keyword=keyword, weight=weight_value))
        return rules

    @staticmethod
    def _parse_negation_rules(items: Iterable[object]) -> List[NegationRule]:
        rules: List[NegationRule] = []
        for item in items:
            if isinstance(item, dict):
                pattern = str(item.get("pattern", "")).strip().lower()
                impact = item.get("impact", -0.5)
            else:
                pattern = str(item).strip().lower()
                impact = -0.5

            if not pattern:
                continue

            try:
                impact_value = float(impact)
            except (TypeError, ValueError):
                impact_value = -0.5

            rules.append(NegationRule(pattern=pattern, impact=impact_value))
        return rules


__all__ = [
    "KeywordRule",
    "NegationRule",
    "ScoringRules",
    "ScoringRulesLoader",
]
