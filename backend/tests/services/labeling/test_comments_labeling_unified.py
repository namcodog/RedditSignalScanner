from __future__ import annotations

from pathlib import Path
import textwrap
import os

from app.services.labeling.labeling_service import _extract_entities_from_text
from app.models.comment import EntityType


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_extract_entities_uses_unified_lexicon(tmp_path, monkeypatch):
    yml = """
    themes:
      demo:
        brands:
          - canonical: "Temu"
          - canonical: "Shein"
    """
    path = _write(tmp_path, "lex/unified.yml", yml)
    monkeypatch.setenv("ENABLE_UNIFIED_LEXICON", "true")
    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(path))

    pairs = _extract_entities_from_text("Temu is rising fast; shein dropships a lot")
    names = {n.lower() for n, _ in pairs}
    assert "temu" in names or "shein" in names
    for _, et in pairs:
        assert et in {EntityType.BRAND, EntityType.PLATFORM}

