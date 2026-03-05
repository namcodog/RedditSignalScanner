import pytest

from app.services.semantic.semantic_scorer import SemanticScorer
from app.services.semantic.unified_lexicon import UnifiedLexicon, SemanticTerm


class DummyTerm:
    def __init__(self, canonical: str, layer: str = "L1", weight: float = 1.0):
        self.canonical = canonical
        self.layer = layer
        self.weight = weight


class DummyLexicon(UnifiedLexicon):
    def __init__(self) -> None:
        pass

    def get_theme_terms(self, theme: str):
        return [
            DummyTerm("foo", "L1", 1.0),
            DummyTerm("bar", "L2", 1.0),
        ]

    def get_patterns_for_matching(self, terms):
        import re

        return [(t.canonical, re.compile(t.canonical)) for t in terms]


def test_semantic_scorer_init_with_lexicon():
    scorer = SemanticScorer(lexicon=DummyLexicon())
    result = scorer.score_theme(["foo is great", "bar appears"], theme="demo")
    assert result.overall_score >= 0
    assert result.unique_terms >= 1


def test_semantic_scorer_requires_source():
    with pytest.raises(ValueError):
        SemanticScorer()
