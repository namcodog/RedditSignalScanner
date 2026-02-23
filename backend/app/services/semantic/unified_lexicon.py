from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import yaml


@dataclass(frozen=True)
class SemanticTerm:
    canonical: str
    aliases: List[str]
    category: str  # brands | features | pain_points
    layer: str  # L1 | L2 | L3 | L4 (若未知则默认 L2)
    precision_tag: str  # exact | phrase | semantic
    weight: float
    polarity: str | None
    lifecycle: str  # seed | candidate | approved


class UnifiedLexicon:
    """统一语义库加载器（只读）。

    - 支持从 unified_lexicon.yml 加载；若不存在则回退到 crossborder_v2.2_calibrated.yml 及同系列结构。
    - 兼容旧格式（themes: {brands/features/pain_points/aliases/exclude/weights}）。
    - layer 缺省时默认 L2；可通过 layer_mapping.csv/… 在后续扩展时补充（此处不强依赖）。
    """

    def __init__(self, config_path: Path) -> None:
        self._config_path = Path(config_path)
        self._data: Dict[str, Any] = {}
        self._themes: Dict[str, Dict[str, Any]] = {}
        self._terms: List[SemanticTerm] = []
        self._theme_index: Dict[str, List[SemanticTerm]] = {}
        self._load()

    # ---------------- Public Queries ----------------

    def get_brands(self, layer: str | None = None) -> List[SemanticTerm]:
        return self._filter_terms("brands", layer)

    def get_features(self, layer: str | None = None) -> List[SemanticTerm]:
        return self._filter_terms("features", layer)

    def get_pain_points(self, layer: str | None = None) -> List[SemanticTerm]:
        return self._filter_terms("pain_points", layer)

    def get_theme_terms(self, theme: str, category: str | None = None) -> List[SemanticTerm]:
        key = str(theme).strip()
        items = list(self._theme_index.get(key, []))
        if category:
            cat = category.strip().lower()
            items = [t for t in items if t.category.lower() == cat]
        return items

    def get_patterns_for_matching(self, terms: List[SemanticTerm]) -> List[Tuple[str, re.Pattern[str]]]:
        """生成匹配模式；与 scripts/score_with_semantic.compile_patterns 一致。"""
        try:
            from scripts.score_with_semantic import compile_patterns  # type: ignore
        except Exception:
            try:
                from backend.scripts.score_with_semantic import compile_patterns  # type: ignore
            except Exception:
                # 兜底：本地实现与 scripts/score_with_semantic.compile_patterns 等价
                def compile_patterns(items: Iterable[str]) -> List[Tuple[str, re.Pattern[str]]]:  # type: ignore
                    out: List[Tuple[str, re.Pattern[str]]] = []
                    for t in items:
                        s = (t or "").strip()
                        if not s:
                            continue
                        esc = re.escape(s)
                        if re.search(r"[A-Za-z]", s):
                            pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
                        else:
                            pat = re.compile(esc, re.IGNORECASE)
                        out.append((s, pat))
                    return out
        return compile_patterns([t.canonical for t in terms])

    def get_layer_definition(self, layer: str) -> Dict[str, Any]:
        """读取层级定义（来自 layer_definitions.yml），失败回退内置默认。

        支持通过环境变量 `SEMANTIC_LAYER_MAP_PATH` 指定路径，否则使用
        `backend/config/semantic_sets/layer_definitions.yml`。
        """
        import os
        from functools import lru_cache

        @lru_cache(maxsize=1)
        def _load_defs() -> Dict[str, Any]:
            cfg_path = os.getenv(
                "SEMANTIC_LAYER_MAP_PATH",
                str(
                    Path(__file__).resolve().parents[3]
                    / "backend/config/semantic_sets/layer_definitions.yml"
                ),
            )
            try:
                p = Path(cfg_path)
                if p.exists():
                    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    return dict(data.get("layers") or {})
            except Exception:
                return {}
            return {}

        name = str(layer or "").upper()
        layers = _load_defs()
        if name in layers:
            return dict(layers[name])
        # fallback minimal
        return {
            "name": name,
            "weight_in_scoring": {"L1": 0.4, "L2": 0.3, "L3": 0.2, "L4": 0.1}.get(name, 0.3),
        }

    # ---------------- Internal ----------------

    def _filter_terms(self, category: str, layer: str | None) -> List[SemanticTerm]:
        cat = category.strip().lower()
        items = [t for t in self._terms if t.category.lower() == cat]
        if layer:
            lay = str(layer).upper()
            items = [t for t in items if (t.layer or "L2").upper() == lay]
        return items

    def _load(self) -> None:
        """Load lexicon data from YAML file."""
        path = self._resolve_path(self._config_path)
        if not path.exists():
            # 双重兜底（避免异常）
            self._data = {"version": 1, "domain": "default", "themes": {}}
            self._themes = {}
            self._terms = []
            self._theme_index = {}
            return

        try:
            self._data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            self._data = {"version": 1, "domain": "default", "themes": {}}

        terms: List[SemanticTerm] = []
        theme_index: Dict[str, List[SemanticTerm]] = {}

        # 1. Try loading 'layers' structure (e.g. crossborder_v2.1.yml)
        layers_data = self._data.get("layers")
        if layers_data and isinstance(layers_data, dict):
            for layer_name, layer_content in layers_data.items():
                # layer_content e.g. {"brands": [...], "features": [...]}
                if not isinstance(layer_content, dict):
                    continue
                for cat in ("brands", "features", "pain_points"):
                    raw_list = list(layer_content.get(cat) or [])
                    for item in raw_list:
                        # item is typically a dict: {"canonical": "...", "weight": ...}
                        if not isinstance(item, dict):
                            continue
                        canonical = str(item.get("canonical") or "").strip()
                        if not canonical:
                            continue
                        term = SemanticTerm(
                            canonical=canonical,
                            aliases=list(item.get("aliases") or []),
                            category=cat,
                            layer=str(item.get("layer") or layer_name),
                            precision_tag=str(item.get("precision_tag") or ("exact" if cat == "brands" else "phrase")),
                            weight=float(item.get("weight") or 1.0),
                            polarity=(str(item.get("polarity")) if item.get("polarity") is not None else None),
                            lifecycle=str(item.get("lifecycle") or "approved"),
                        )
                        terms.append(term)
            self._terms = terms
            self._theme_index = theme_index  # Layers structure might not have themes, keep empty or infer?
            return

        # 2. Fallback to 'themes' structure (old format)
        themes = dict(self._data.get("themes") or {})
        self._themes = themes
        for theme, cfg in themes.items():
            weights: Mapping[str, float] = cfg.get("weights") or {"brands": 1.5, "features": 1.0, "pain_points": 1.2}
            default_layer = str(cfg.get("default_layer") or "L2")
            # 兼容两种结构：
            # 1) 旧格式：category -> ["Amazon", "Shopify"] + aliases 映射
            # 2) 新格式：category -> [ {canonical, aliases, layer, precision_tag, weight, polarity, lifecycle}, ...]
            aliases_map: Mapping[str, List[str]] = cfg.get("aliases") or {}
            for cat in ("brands", "features", "pain_points"):
                raw_list = list(cfg.get(cat) or [])
                for item in raw_list:
                    if isinstance(item, str):
                        canonical = str(item)
                        term = SemanticTerm(
                            canonical=canonical,
                            aliases=list(aliases_map.get(canonical, [])),
                            category=cat,
                            layer=default_layer,
                            precision_tag="exact" if cat == "brands" else "phrase",
                            weight=float(weights.get(cat, 1.0)),
                            polarity=None,
                            lifecycle="approved",
                        )
                    else:
                        canonical = str(item.get("canonical") or "").strip()
                        if not canonical:
                            continue
                        term = SemanticTerm(
                            canonical=canonical,
                            aliases=list(item.get("aliases") or aliases_map.get(canonical, []) or []),
                            category=cat,
                            layer=str(item.get("layer") or default_layer or "L2"),
                            precision_tag=str(item.get("precision_tag") or ("exact" if cat == "brands" else "phrase")),
                            weight=float(item.get("weight") or weights.get(cat, 1.0) or 1.0),
                            polarity=(str(item.get("polarity")) if item.get("polarity") is not None else None),
                            lifecycle=str(item.get("lifecycle") or "approved"),
                        )
                    terms.append(term)
                    theme_index.setdefault(theme, []).append(term)
        self._terms = terms
        self._theme_index = theme_index

    @staticmethod
    def _resolve_path(user_path: Path) -> Path:
        p = Path(user_path)
        if p.exists():
            return p
        # fallback 到校准版
        # __file__ = backend/app/services/semantic/unified_lexicon.py
        # parents[4] → repo root
        repo_root = Path(__file__).resolve().parents[4]
        fallback = repo_root / "backend" / "config" / "semantic_sets" / "crossborder_v2.2_calibrated.yml"
        return fallback


    @classmethod
    def from_terms(
        cls,
        terms: Iterable[Mapping[str, Any]],
        *,
        default_layer: str = "L2",
    ) -> "UnifiedLexicon":
        """Construct a lexicon instance from flat term records (e.g. database rows).

        Each term mapping is expected to provide:
        - canonical, category
        - aliases (optional list[str])
        - layer, precision_tag, weight, polarity, lifecycle (all optional)
        """
        # Bypass __init__/_load YAML path; this instance is DB-backed only.
        self: "UnifiedLexicon" = cls.__new__(cls)  # type: ignore[call-arg]
        self._config_path = Path("__db__")
        self._data = {}
        self._themes = {}

        built_terms: list[SemanticTerm] = []
        for raw in terms:
            canonical = str(raw.get("canonical") or "").strip()
            category = str(raw.get("category") or "").strip()
            if not canonical or not category:
                continue
            aliases = list(raw.get("aliases") or [])
            layer = str(raw.get("layer") or default_layer)
            precision_tag = str(
                raw.get("precision_tag")
                or ("exact" if category == "brands" else "phrase")
            )
            weight_val = raw.get("weight")
            try:
                weight = float(weight_val) if weight_val is not None else 1.0
            except (TypeError, ValueError):
                weight = 1.0
            polarity_val = raw.get("polarity")
            polarity = str(polarity_val) if polarity_val is not None else None
            lifecycle = str(raw.get("lifecycle") or "approved")

            built_terms.append(
                SemanticTerm(
                    canonical=canonical,
                    aliases=aliases,
                    category=category,
                    layer=layer,
                    precision_tag=precision_tag,
                    weight=weight,
                    polarity=polarity,
                    lifecycle=lifecycle,
                )
            )

        self._terms = built_terms
        self._theme_index = {}
        return self


__all__ = ["UnifiedLexicon", "SemanticTerm"]
