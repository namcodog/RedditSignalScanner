from __future__ import annotations

from pathlib import Path
import textwrap
import os

import pytest

from app.services.semantic.unified_lexicon import UnifiedLexicon, SemanticTerm


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_load_from_valid_yaml(tmp_path: Path) -> None:
    yml = """
    themes:
      crossborder:
        weights: {brands: 1.5, features: 1.0, pain_points: 1.2}
        brands:
          - canonical: "Amazon"
            aliases: ["AMZN"]
            layer: "L1"
            precision_tag: "exact"
            weight: 1.5
            polarity: neutral
            lifecycle: approved
        features:
          - canonical: "FBA"
            aliases: ["Fulfillment by Amazon"]
            layer: "L2"
            precision_tag: "exact"
            weight: 1.0
            polarity: positive
            lifecycle: approved
        pain_points:
          - canonical: "saturated market"
            aliases: ["saturated", "oversaturated"]
            layer: "L4"
            precision_tag: "phrase"
            weight: 1.2
            polarity: negative
            lifecycle: approved
    """
    path = _write(tmp_path, "lex/unified.yml", yml)
    lx = UnifiedLexicon(path)
    brands = lx.get_brands()
    assert any(t.canonical == "Amazon" and t.layer == "L1" for t in brands)
    assert len(lx.get_features()) == 1
    assert len(lx.get_pain_points()) == 1
    # theme terms
    tts = lx.get_theme_terms("crossborder", category="brands")
    assert len(tts) == 1 and tts[0].canonical == "Amazon"


def test_load_from_invalid_yaml(tmp_path: Path) -> None:
    bad = """
    themes:
      broken: [this-is-not: valid
    """
    path = _write(tmp_path, "lex/bad.yml", bad)
    lx = UnifiedLexicon(path)
    # invalid YAML → empty/default structure, not crashing
    assert lx.get_brands() == []
    assert lx.get_features() == []
    assert lx.get_pain_points() == []


def test_load_from_missing_file() -> None:
    # _resolve_path 会回退到仓库内的 crossborder_v2.2_calibrated.yml
    p = UnifiedLexicon._resolve_path(Path("/non/existent/unified.yml"))  # type: ignore[attr-defined]
    assert p.exists()
    lx = UnifiedLexicon(Path("/really/not/there.yml"))
    # 至少保证接口不报错并返回 list 类型
    assert isinstance(lx.get_brands(), list)


def test_get_brands_by_layer(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands:
          - canonical: "Amazon"
            layer: "L1"
          - canonical: "Etsy"
            layer: "L1"
          - canonical: "SomeTool"
            layer: "L3"
    """
    path = _write(tmp_path, "lex/layered.yml", yml)
    lx = UnifiedLexicon(path)
    l1 = lx.get_brands(layer="l1")
    assert {t.canonical for t in l1} == {"Amazon", "Etsy"}
    l3 = lx.get_brands(layer="L3")
    assert {t.canonical for t in l3} == {"SomeTool"}


def test_get_patterns_for_matching(tmp_path: Path) -> None:
    yml = """
    themes:
      demo:
        brands: ["Amazon"]
        features: ["dropshipping"]
    """
    path = _write(tmp_path, "lex/pattern.yml", yml)
    lx = UnifiedLexicon(path)
    terms = lx.get_brands() + lx.get_features()
    pats = lx.get_patterns_for_matching(terms)
    # 确认正则包含单词边界（英文）
    dict_pats = {t: p for t, p in pats}
    assert "Amazon" in dict_pats and "dropshipping" in dict_pats
    assert "\\bAmazon\\b" in dict_pats["Amazon"].pattern


def test_get_layer_definition_reads_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    layer_yaml = """
    layers:
      L1:
        name: "决策层"
        weight_in_scoring: 0.4
      L2:
        name: "执行层"
        weight_in_scoring: 0.3
    """
    def_path = _write(tmp_path, "conf/layer_definitions.yml", layer_yaml)
    monkeypatch.setenv("SEMANTIC_LAYER_MAP_PATH", str(def_path))
    # 路径无需真实存在 lexicon，只用于触发读取 layer 定义
    lx = UnifiedLexicon(Path("/no/such/unified.yml"))
    meta = lx.get_layer_definition("L1")
    assert isinstance(meta, dict)
    assert meta.get("name") == "决策层"
    assert float(meta.get("weight_in_scoring", 0.0)) == 0.4

