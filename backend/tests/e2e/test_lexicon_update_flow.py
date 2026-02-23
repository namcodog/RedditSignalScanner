from __future__ import annotations

from pathlib import Path
import textwrap

from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.labeling import _extract_entities_from_text


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_e2e_lexicon_update_enables_new_brand_detection(tmp_path, monkeypatch):
    base = """
    themes:
      unified:
        brands: []
        features: []
        pain_points: []
    """
    lex_path = _write(tmp_path, "lex/base.yml", base)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(lex_path))

    # Before update: not detected
    pairs_before = _extract_entities_from_text("Temu and Shein surge")
    assert not any(n.lower() == "temu" for n, _ in pairs_before)

    # Write a merged file (simulate migration result)
    merged = """
    themes:
      unified:
        brands: ["Temu", "Shein"]
        features: []
        pain_points: []
    """
    lex_path.write_text(textwrap.dedent(merged).lstrip(), encoding="utf-8")

    # After update: detected
    pairs_after = _extract_entities_from_text("Temu and Shein surge")
    assert any(n.lower() == "temu" for n, _ in pairs_after)

