from __future__ import annotations

from pathlib import Path
import textwrap

from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.semantic.semantic_scorer import SemanticScorer


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_semantic_scorer_layer_coverage_and_penalty(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands:
          - canonical: "Amazon"
            layer: "L1"
            weight: 1.5
        features:
          - canonical: "FBA"
            layer: "L2"
            weight: 1.0
        pain_points:
          - canonical: "saturated"
            layer: "L4"
            weight: 1.2
    """
    path = _write(tmp_path, "lex/u.yml", yml)
    lex = UnifiedLexicon(path)
    scorer = SemanticScorer(lexicon=lex, enable_layered=True)

    texts1 = [
        "We use FBA and see saturated competition",  # L2 + L4, no L1
        "FBA workflow is getting easier",
    ]
    r1 = scorer.score_theme(texts1, "demo")
    assert 0.0 <= r1.overall_score <= 100.0
    assert r1.layer_coverage.get("L1", 0.0) == 0.0
    penalized_score = r1.overall_score

    texts2 = [
        "Amazon FBA beats others",
        "Saturated market on Amazon makes it hard",
    ]
    r2 = scorer.score_theme(texts2, "demo")
    assert r2.layer_coverage.get("L1", 0.0) > 0.0
    assert r2.overall_score >= penalized_score  # 有 L1 时分数不应低于被罚版本


def test_semantic_scorer_legacy_mode(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon"]
        features: ["FBA"]
        pain_points: ["saturated"]
    """
    path = _write(tmp_path, "lex/u2.yml", yml)
    lex = UnifiedLexicon(path)
    scorer = SemanticScorer(lexicon=lex, enable_layered=False)
    texts = ["Amazon FBA", "Market is saturated"]
    r = scorer.score_theme(texts, "demo")
    assert 0.0 <= r.overall_score <= 100.0
    assert r.layer_coverage == {}

