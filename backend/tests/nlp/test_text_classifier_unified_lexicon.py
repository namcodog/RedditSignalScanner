from __future__ import annotations

from pathlib import Path
import textwrap
import os

from app.models.comment import Category
from app.services.semantic.text_classifier import classify_category_aspect


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_classifier_uses_unified_lexicon_for_category(tmp_path, monkeypatch):
    yml = """
    themes:
      demo:
        features:
          - canonical: "private label"
            layer: "L2"
        pain_points:
          - canonical: "account suspension"
            layer: "L4"
    """
    lex_path = _write(tmp_path, "lex/unified.yml", yml)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(lex_path))

    c1 = classify_category_aspect("We were hit by account suspension last week")
    assert c1.category == Category.PAIN

    c2 = classify_category_aspect("We plan to start with private label on Amazon")
    assert c2.category == Category.SOLUTION

