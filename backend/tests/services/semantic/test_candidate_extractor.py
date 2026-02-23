from __future__ import annotations

from pathlib import Path
import textwrap

from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.semantic.candidate_extractor import CandidateExtractor


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_candidate_extractor_from_texts_excludes_known_terms(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon"]
        features: ["FBA"]
        pain_points: []
    """
    path = _write(tmp_path, "lex/u.yml", yml)
    lex = UnifiedLexicon(path)
    ext = CandidateExtractor(lexicon=lex, min_frequency=2)
    texts = [
        "Temu is rising, Temu discounts everywhere",
        "TikTok Shop creators grow fast",
        "Amazon dominates (should be excluded)",
        "Shein and TEMU battle",
    ]
    cands = ext.extract_from_texts(texts)
    names = [c.canonical for c in cands]
    assert "Amazon" not in names
    assert any("Temu" in n for n in names)


def test_candidate_export_to_csv(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: []
        features: []
        pain_points: []
    """
    path = _write(tmp_path, "lex/u2.yml", yml)
    lex = UnifiedLexicon(path)
    ext = CandidateExtractor(lexicon=lex, min_frequency=1)
    texts = ["Shein Shein", "Temu"]
    cands = ext.extract_from_texts(texts)
    out = tmp_path / "candidates.csv"
    ext.export_to_csv(cands, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "canonical,aliases,confidence" in content.splitlines()[0]
