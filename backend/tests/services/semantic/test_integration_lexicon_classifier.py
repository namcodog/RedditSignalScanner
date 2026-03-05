from __future__ import annotations

import importlib
import os
import textwrap
from pathlib import Path

import pytest


def _write_lex(p: Path) -> None:
    p.write_text(
        textwrap.dedent(
            """
            version: 1
            domain: test
            themes:
              demo:
                brands: ["TemuX"]
                features: ["pricingtrap"]
                pain_points: ["subscription fee"]
                aliases: { TemuX: ["TEMUX"] }
                exclude: []
                weights: { brands: 1.5, features: 1.0, pain_points: 1.2 }
            """
        ).strip(),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_text_classifier_uses_unified_lexicon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yml = tmp_path / "unified.yml"
    _write_lex(yml)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(yml))

    # reload modules to pick up settings
    mod = importlib.import_module("app.services.semantic.text_classifier")
    importlib.reload(mod)

    cls = mod.classify_category_aspect("we discuss pricingtrap here")
    assert cls.aspect.name == "PRICE"


@pytest.mark.asyncio
async def test_comments_labeling_uses_unified_lexicon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yml = tmp_path / "unified.yml"
    _write_lex(yml)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(yml))

    mod = importlib.import_module("app.services.labeling.comments_labeling")
    importlib.reload(mod)
    extracted = mod._extract_entities_from_text("We love TemuX deals!")
    names = [n for n, _ in extracted]
    assert "temux" in names
