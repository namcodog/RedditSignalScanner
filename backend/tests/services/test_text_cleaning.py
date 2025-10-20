from __future__ import annotations

from app.services.analysis.text_cleaner import clean_text, score_with_context
from app.services.analysis.opportunity_scorer import OpportunityScorer
from app.services.analysis.scoring_rules import KeywordRule, NegationRule, ScoringRules


class _StubLoader:
    def __init__(self) -> None:
        self.rules = ScoringRules(
            positive_keywords=[KeywordRule("need", 0.2)],
            negative_keywords=[KeywordRule("giveaway", -0.3)],
            negation_patterns=[NegationRule("not interested", -0.6)],
        )

    def load(self) -> ScoringRules:
        return self.rules


def test_clean_text_removes_urls_code_and_quotes() -> None:
    raw = (
        "Check this out https://example.com\n"
        "> quoted line\n"
        "```\nignored\n```\n"
        "Inline `code` remains?"
    )

    cleaned = clean_text(raw)

    assert "http" not in cleaned
    assert ">" not in cleaned
    assert "ignored" not in cleaned
    assert "code" not in cleaned
    assert cleaned == "Check this out Inline remains?"


def test_score_with_context_uses_window_and_scoring() -> None:
    sentences = [
        "Need an automation assistant",
        "We must have weekly research summaries",
        "Manual updates slow us down",
    ]
    scorer = OpportunityScorer(loader=_StubLoader())

    center_score = score_with_context(sentences, 1, scorer=scorer)
    edge_score = score_with_context(sentences, 2, scorer=scorer)

    assert center_score > 0.0
    assert edge_score < center_score
