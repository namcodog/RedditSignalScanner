from __future__ import annotations

import textwrap
from pathlib import Path

from app.services.discovery.warzone_classifier import WarzoneClassifier


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_warzone_classifier_guesses_vertical_from_texts(tmp_path: Path) -> None:
    yml = """
    warzones:
      Ecommerce_Business:
        keywords: ["shopify", "facebook ads", "roas"]
      Tools_EDC:
        keywords: ["multitool", "torx", "ratchet"]
    """
    cfg = _write(tmp_path, "warzones.yml", yml)
    clf = WarzoneClassifier(cfg)

    guess = clf.classify_texts(
        [
            "Need help with Shopify ROAS dropping",
            "Facebook ads attribution is broken",
        ]
    )
    assert guess.warzone == "Ecommerce_Business"
    assert guess.confidence > 0
    assert any("shopify" in r.lower() for r in guess.reasons)


def test_warzone_classifier_returns_unknown_when_no_hits(tmp_path: Path) -> None:
    yml = """
    warzones:
      Ecommerce_Business:
        keywords: ["shopify"]
    """
    cfg = _write(tmp_path, "warzones.yml", yml)
    clf = WarzoneClassifier(cfg)

    guess = clf.classify_texts(["totally unrelated cooking tips"])
    assert guess.warzone in {"unknown", ""}
    assert guess.confidence == 0.0

