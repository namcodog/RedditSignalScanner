"""Template matching utilities for opportunity scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Pattern, Sequence

from app.services.analysis.scoring_templates import (
    NegativeTemplate,
    PositiveTemplate,
    TemplateConfigLoader,
)


@dataclass(frozen=True)
class TemplateMatchResult:
    positive_matches: List[str]
    negative_matches: List[str]
    boost: float
    penalty: float


class TemplateMatcher:
    """Compile and apply regex templates for opportunity text."""

    def __init__(self, loader: TemplateConfigLoader | None = None) -> None:
        self._loader = loader or TemplateConfigLoader()
        self._positive: List[tuple[PositiveTemplate, Pattern[str]]] = []
        self._negative: List[tuple[NegativeTemplate, Pattern[str]]] = []
        self._compile_templates()

    def _compile_templates(self) -> None:
        templates = self._loader.load()
        self._positive = [
            (tmpl, re.compile(tmpl.pattern, re.IGNORECASE)) for tmpl in templates.positives
        ]
        self._negative = [
            (tmpl, re.compile(tmpl.pattern, re.IGNORECASE)) for tmpl in templates.negatives
        ]

    def refresh(self) -> None:
        self._compile_templates()

    def match(self, text: str) -> TemplateMatchResult:
        if not text:
            return TemplateMatchResult([], [], 0.0, 0.0)

        lowered = text.lower()
        positive_hits: List[str] = []
        negative_hits: List[str] = []
        boost_total = 0.0
        penalty_total = 0.0

        for pos_template, pattern in self._positive:
            if pattern.search(lowered):
                positive_hits.append(pos_template.name)
                boost_total += max(0.0, pos_template.boost)

        for neg_template, pattern in self._negative:
            if pattern.search(lowered):
                negative_hits.append(neg_template.name)
                penalty_total += max(0.0, neg_template.penalty)

        return TemplateMatchResult(positive_hits, negative_hits, boost_total, penalty_total)


__all__ = ["TemplateMatcher", "TemplateMatchResult"]
