from __future__ import annotations

import pytest

from app.services.analysis.opportunity_scorer import OpportunityScorer, ScoringResult
from app.services.analysis.scoring_rules import KeywordRule, NegationRule, ScoringRules
from app.services.analysis.template_matcher import TemplateMatchResult


class _StubLoader:
    def __init__(self, rules: ScoringRules) -> None:
        self._rules = rules

    def load(self) -> ScoringRules:
        return self._rules


class _StubTemplateMatcher:
    def __init__(self, result: TemplateMatchResult | None = None) -> None:
        self._result = result or TemplateMatchResult([], [], 0.0, 0.0)

    def refresh(self) -> None:
        pass

    def match(self, text: str) -> TemplateMatchResult:
        return self._result


def _make_scorer(
    *,
    positives: list[tuple[str, float]],
    negatives: list[tuple[str, float]],
    negations: list[tuple[str, float]],
    template_result: TemplateMatchResult | None = None,
) -> OpportunityScorer:
    rules = ScoringRules(
        positive_keywords=[KeywordRule(k.lower(), w) for k, w in positives],
        negative_keywords=[KeywordRule(k.lower(), w) for k, w in negatives],
        negation_patterns=[NegationRule(p.lower(), impact) for p, impact in negations],
    )
    loader = _StubLoader(rules)
    matcher = _StubTemplateMatcher(template_result)
    return OpportunityScorer(loader=loader, template_matcher=matcher)


def test_positive_keywords_increase_score() -> None:
    scorer = _make_scorer(
        positives=[("need", 0.1), ("willing to pay", 0.15)],
        negatives=[],
        negations=[],
    )

    result = scorer.score("We need an assistant and are willing to pay for it")

    assert isinstance(result, ScoringResult)
    assert result.base_score > 0.2
    assert "need" in result.positive_hits
    assert result.negative_hits == []
    assert result.negated is False
    assert result.template_boost == 0.0
    assert result.template_penalty == 0.0


def test_negative_keywords_reduce_score() -> None:
    scorer = _make_scorer(
        positives=[("need", 0.12)],
        negatives=[("giveaway", -0.25)],
        negations=[],
    )

    result = scorer.score("Need a solution but this giveaway idea is not serious")

    assert result.base_score == pytest.approx(0.0, abs=1e-6)
    assert "giveaway" in result.negative_hits
    assert result.template_boost == 0.0
    assert result.template_penalty == 0.0


def test_negation_patterns_zero_out_score() -> None:
    scorer = _make_scorer(
        positives=[("need", 0.2)],
        negatives=[],
        negations=[("not interested", -0.6)],
    )

    result = scorer.score("We need automation but we're not interested right now")

    assert result.negated is True
    assert result.base_score == 0.0
    assert result.template_boost == 0.0
    assert result.template_penalty == 0.0


def test_template_boosts_score() -> None:
    template_result = TemplateMatchResult(["budget"], [], 0.3, 0.0)
    scorer = _make_scorer(
        positives=[("need", 0.1)],
        negatives=[],
        negations=[],
        template_result=template_result,
    )

    result = scorer.score("Need automation with $50 budget")

    assert result.template_boost >= 0.3
    assert "budget" in result.template_positive
    assert result.base_score > 0.3


def test_template_penalty_reduces_score() -> None:
    template_result = TemplateMatchResult([], ["giveaway"], 0.0, 0.5)
    scorer = _make_scorer(
        positives=[("need", 0.3)],
        negatives=[],
        negations=[],
        template_result=template_result,
    )

    result = scorer.score("Need automation but this is a giveaway")

    assert result.template_penalty >= 0.5
    assert "giveaway" in result.template_negative
    assert result.base_score == pytest.approx(0.0, abs=1e-6)
