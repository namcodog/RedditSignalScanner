"""Opportunity scoring utilities based on configurable keyword rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from app.services.analysis.scoring_rules import (
    KeywordRule,
    NegationRule,
    ScoringRules,
    ScoringRulesLoader,
)
from app.services.analysis.template_matcher import TemplateMatcher


@dataclass
class ScoringResult:
    base_score: float
    positive_hits: list[str]
    negative_hits: list[str]
    negated: bool
    template_positive: list[str]
    template_negative: list[str]
    template_boost: float
    template_penalty: float


class OpportunityScorer:
    """Compute opportunity scores leveraging positive/negative keyword rules."""

    def __init__(
        self,
        loader: ScoringRulesLoader | None = None,
        template_matcher: TemplateMatcher | None = None,
    ) -> None:
        self._loader = loader or ScoringRulesLoader()
        self._rules = self._loader.load()
        self._template_matcher = template_matcher or TemplateMatcher()

    def refresh(self) -> None:
        """Force reload of rule configuration."""
        self._rules = self._loader.load()
        self._template_matcher.refresh()

    def score(self, text: str) -> ScoringResult:
        if not text:
            return ScoringResult(0.0, [], [], False, [], [], 0.0, 0.0)

        self.refresh()
        lowered = text.lower()
        positive_hits = self._collect_hits(lowered, self._rules.positive_keywords)
        negative_hits = self._collect_hits(lowered, self._rules.negative_keywords)
        negated = self._has_negation(lowered, self._rules.negation_patterns)

        template_result = self._template_matcher.match(lowered)

        base_score = 0.0
        for keyword in positive_hits:
            base_score += self._weight_for(keyword, self._rules.positive_keywords)
        for keyword in negative_hits:
            base_score += self._weight_for(keyword, self._rules.negative_keywords)

        base_score += template_result.boost
        base_score -= template_result.penalty

        if negated:
            base_score = min(base_score, 0.0)

        base_score = max(0.0, min(1.0, base_score))
        return ScoringResult(
            base_score,
            positive_hits,
            negative_hits,
            negated,
            template_result.positive_matches,
            template_result.negative_matches,
            template_result.boost,
            template_result.penalty,
        )

    @staticmethod
    def _collect_hits(text: str, rules: Sequence[KeywordRule]) -> list[str]:
        hits: list[str] = []
        for rule in rules:
            if rule.keyword and rule.keyword in text:
                hits.append(rule.keyword)
        return hits

    @staticmethod
    def _weight_for(keyword: str, rules: Sequence[KeywordRule]) -> float:
        for rule in rules:
            if rule.keyword == keyword:
                return float(rule.weight)
        return 0.0

    @staticmethod
    def _has_negation(text: str, rules: Sequence[NegationRule]) -> bool:
        for rule in rules:
            if rule.pattern and rule.pattern in text:
                return True
        return False


__all__ = ["OpportunityScorer", "ScoringResult"]
