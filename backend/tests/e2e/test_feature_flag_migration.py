from __future__ import annotations

from pathlib import Path
import textwrap

from app.services.text_classifier import classify_category_aspect
from app.models.comment import Category
from app.services.labeling import _extract_entities_from_text


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_feature_flag_toggle_affects_classification_and_entities(tmp_path, monkeypatch):
    # Prepare lexicon with terms that are NOT in hardcoded keyword lists
    yml = """
    themes:
      unified:
        brands: ["Temu"]
        features: ["private label"]
        pain_points: ["account suspension"]
    """
    lex_path = _write(tmp_path, "lex/unified.yml", yml)
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(lex_path))

    text_pain = "We faced account suspension last night"
    text_solution = "Exploring private label to start"
    text_brand = "Temu is trending"

    # Flag OFF → fall back to old logic (should not classify as PAIN/SOLUTION for these phrases)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "false")
    c1 = classify_category_aspect(text_pain)
    c2 = classify_category_aspect(text_solution)
    ents_off = _extract_entities_from_text(text_brand)
    assert c1.category in {Category.OTHER, Category.PAIN}  # old rules may mark PAIN rarely, accept both
    assert c2.category in {Category.OTHER, Category.SOLUTION}
    assert not any(n.lower() == "temu" for n, _ in ents_off)

    # Flag ON → use UnifiedLexicon results
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    c1_on = classify_category_aspect(text_pain)
    c2_on = classify_category_aspect(text_solution)
    ents_on = _extract_entities_from_text(text_brand)

    assert c1_on.category == Category.PAIN
    assert c2_on.category == Category.SOLUTION
    assert any(n.lower() == "temu" for n, _ in ents_on)

