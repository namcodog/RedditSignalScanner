"""Loader for opportunity scoring templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, List

import yaml


@dataclass(frozen=True)
class PositiveTemplate:
    name: str
    pattern: str
    boost: float


@dataclass(frozen=True)
class NegativeTemplate:
    name: str
    pattern: str
    penalty: float


@dataclass(frozen=True)
class ScoringTemplates:
    positives: List[PositiveTemplate]
    negatives: List[NegativeTemplate]


class TemplateConfigLoader:
    """Load template configuration with lightweight caching."""

    def __init__(self, config_path: Path | None = None) -> None:
        base = Path(__file__).resolve()
        if config_path is None:
            resolved = None
            for parent in base.parents:
                candidate = parent / "config" / "scoring_templates.yaml"
                if candidate.exists():
                    resolved = candidate
                    break
            if resolved is None:
                resolved = Path.cwd() / "config" / "scoring_templates.yaml"
            self._path = resolved
        else:
            self._path = config_path
        self._cache: ScoringTemplates | None = None
        self._mtime: float | None = None
        self._lock = Lock()

    def load(self) -> ScoringTemplates:
        with self._lock:
            current_mtime = self._path.stat().st_mtime
            if self._cache is not None and current_mtime == self._mtime:
                return self._cache

            with self._path.open("r", encoding="utf-8") as fh:
                payload = yaml.safe_load(fh) or {}

            templates = ScoringTemplates(
                positives=self._parse_positive(payload.get("positive", [])),
                negatives=self._parse_negative(payload.get("negative", [])),
            )

            self._cache = templates
            self._mtime = current_mtime
            return templates

    @staticmethod
    def _parse_positive(items: Iterable[object]) -> List[PositiveTemplate]:
        templates: List[PositiveTemplate] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip() or "positive"
            pattern = str(item.get("pattern", "")).strip()
            boost = item.get("boost", 0.2)
            try:
                boost_value = float(boost)
            except (TypeError, ValueError):
                boost_value = 0.2
            if pattern:
                templates.append(PositiveTemplate(name=name, pattern=pattern, boost=boost_value))
        return templates

    @staticmethod
    def _parse_negative(items: Iterable[object]) -> List[NegativeTemplate]:
        templates: List[NegativeTemplate] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip() or "negative"
            pattern = str(item.get("pattern", "")).strip()
            penalty = item.get("penalty", 0.2)
            try:
                penalty_value = float(penalty)
            except (TypeError, ValueError):
                penalty_value = 0.2
            if pattern:
                templates.append(
                    NegativeTemplate(name=name, pattern=pattern, penalty=penalty_value)
                )
        return templates


__all__ = [
    "PositiveTemplate",
    "NegativeTemplate",
    "ScoringTemplates",
    "TemplateConfigLoader",
]
