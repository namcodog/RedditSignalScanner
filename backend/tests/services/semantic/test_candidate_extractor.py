from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

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


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)


class _FakeSession:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, stmt):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("comments query unavailable")
        if self.calls == 2:
            return _Result([("Temu analytics", 101), ("Temu analytics", 102)])
        return _Result([])


class _FakeRepository:
    def __init__(self) -> None:
        self.source = ""
        self.items = []

    async def bulk_upsert(self, items, source: str):
        self.items = list(items)
        self.source = source
        return []


@pytest.mark.asyncio
async def test_candidate_extractor_records_fallback_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yml = """
    themes:
      demo:
        brands: []
        features: []
        pain_points: []
    """
    path = _write(tmp_path, "lex/u3.yml", yml)
    lex = UnifiedLexicon(path)
    ext = CandidateExtractor(lexicon=lex, min_frequency=1)
    repo = _FakeRepository()
    diagnostics: dict[str, object] = {}

    async def _fake_relation(_session) -> str:
        return "comments"

    monkeypatch.setattr(
        "app.services.semantic.candidate_extractor.get_comments_core_lab_relation",
        _fake_relation,
    )

    await ext.extract_from_db(
        _FakeSession(),
        repo,
        lookback_days=90,
        diagnostics=diagnostics,
    )

    assert repo.source == "posts_fallback"
    assert diagnostics["candidate_extract_source"] == "posts_fallback"
    assert diagnostics["candidate_extract_status"] == "posts_fallback"
    assert diagnostics["candidate_extract_error"] == "comments query unavailable"
