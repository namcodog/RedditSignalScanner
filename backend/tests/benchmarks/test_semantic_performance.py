from __future__ import annotations

import time
from pathlib import Path
import textwrap

from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.semantic.semantic_scorer import SemanticScorer


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_lexicon_load_time(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon", "Shopify", "Etsy", "Temu", "Shein"]
        features: ["FBA", "dropshipping", "private label"]
        pain_points: ["saturated", "account suspension"]
    """
    path = _write(tmp_path, "lex/u.yml", yml)
    t0 = time.perf_counter()
    _ = UnifiedLexicon(path)
    dt = (time.perf_counter() - t0) * 1000.0
    assert dt < 500.0


def test_single_text_scoring_time(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon", "Shopify", "Etsy"]
        features: ["FBA", "ads"]
        pain_points: ["saturated"]
    """
    path = _write(tmp_path, "lex/u2.yml", yml)
    lex = UnifiedLexicon(path)
    scorer = SemanticScorer(lexicon=lex, enable_layered=True)
    text = ["Amazon FBA saturated market ads ads"]
    t0 = time.perf_counter()
    _ = scorer.score_theme(text, "demo")
    dt = (time.perf_counter() - t0) * 1000.0
    assert dt < 50.0


def test_batch_scoring_time(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon", "Shopify", "Etsy", "Temu", "Shein"]
        features: ["FBA", "ads", "seo", "listing", "catalog"]
        pain_points: ["saturated", "infringement", "compliance"]
    """
    path = _write(tmp_path, "lex/u3.yml", yml)
    lex = UnifiedLexicon(path)
    scorer = SemanticScorer(lexicon=lex, enable_layered=True)
    texts = ["Amazon FBA ads saturated market"] * 2000  # small but meaningful batch
    t0 = time.perf_counter()
    for i in range(0, len(texts), 20):
        _ = scorer.score_theme(texts[i : i + 20], "demo")
    dt = time.perf_counter() - t0
    assert dt < 30.0  # seconds

