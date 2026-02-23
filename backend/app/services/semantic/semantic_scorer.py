from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from app.interfaces.semantic_provider import SemanticProvider
from app.services.semantic.unified_lexicon import UnifiedLexicon, SemanticTerm
import asyncio


@dataclass
class ScoringResult:
    overall_score: float
    layer_coverage: Dict[str, float]
    weighted_density: float
    coverage: float
    density: float
    purity: float
    mentions: int
    unique_terms: int
    tokens: int


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}")


def _token_count(texts: Iterable[str]) -> int:
    total = 0
    for txt in texts:
        total += len(_TOKEN.findall(txt or ""))
    return max(1, total)


class SemanticScorer:
    def __init__(
        self,
        lexicon: UnifiedLexicon | None = None,
        enable_layered: bool = True,
        semantic_provider: SemanticProvider | None = None,
    ) -> None:
        if lexicon is None and semantic_provider is None:
            raise ValueError("SemanticScorer requires lexicon or semantic_provider")
        if lexicon is None and semantic_provider is not None:
            # 同步上下文中使用，直接阻塞式加载
            lexicon = asyncio.run(semantic_provider.load())
        self._lex = lexicon  # type: ignore[assignment]
        self._enable_layered = bool(enable_layered)

    def score_theme(self, texts: List[str], theme: str) -> ScoringResult:
        # 收集主题所有词条
        terms = self._lex.get_theme_terms(theme)
        if not terms:
            return ScoringResult(0.0, {}, 0.0, 0.0, 0.0, 1.0, 0, 0, _token_count(texts))

        # 预编译模式（仅使用 canonical 参与匹配，保持一致性）
        pats = self._lex.get_patterns_for_matching(terms)
        excl_pats: List[Tuple[str, re.Pattern[str]]] = []
        # exclude 列表在旧格式里是字符串；这里按惯例忽略（可在未来加入 lexicon.get_excludes(theme)）

        # 计数
        hits: Dict[str, int] = {t.canonical: 0 for t in terms}
        for canon, pat in pats:
            for txt in texts:
                hits[canon] += len(pat.findall(txt or ""))
        excl_hits = 0
        for _t, pat in excl_pats:
            for txt in texts:
                excl_hits += len(pat.findall(txt or ""))

        unique = sum(1 for k, v in hits.items() if v > 0)
        total_terms = max(1, len(terms))
        coverage = unique / total_terms

        total_tokens = _token_count(texts)
        total_mentions = sum(hits.values())
        # 加权密度：按 term.weight 加权，tokens 归一化
        weight_map: Dict[str, float] = {t.canonical: float(t.weight or 1.0) for t in terms}
        weighted_mentions = sum((hits[k] * weight_map.get(k, 1.0)) for k in hits)
        density = min(1.0, total_mentions / max(10.0, total_tokens / 50.0))
        weighted_density = min(1.0, weighted_mentions / max(10.0, total_tokens / 50.0))
        purity = 1.0 - (excl_hits / max(1.0, excl_hits + total_mentions))

        if not self._enable_layered:
            # 旧算法：coverage×density×purity 的指数加权（与脚本保持近似）
            alpha, beta, gamma = 0.5, 0.3, 0.2
            score = (coverage ** alpha) * (density ** beta) * (purity ** gamma)
            score = max(0.0, min(1.0, float(score))) * 100.0
            return ScoringResult(
                overall_score=score,
                layer_coverage={},
                weighted_density=weighted_density,
                coverage=coverage,
                density=density,
                purity=purity,
                mentions=int(total_mentions),
                unique_terms=int(unique),
                tokens=int(total_tokens),
            )

        # 分层覆盖率
        layers = ("L1", "L2", "L3", "L4")
        layer_hits: Dict[str, Tuple[int, int]] = {L: (0, 0) for L in layers}  # (unique_hit, total_terms)
        for L in layers:
            layer_terms = [t for t in terms if (t.layer or "L2").upper() == L]
            if not layer_terms:
                continue
            uniq = sum(1 for t in layer_terms if hits.get(t.canonical, 0) > 0)
            layer_hits[L] = (uniq, len(layer_terms))
        layer_cov = {L: (uh / max(1, tt)) for L, (uh, tt) in layer_hits.items()}

        # 加权汇总（来自设计文档）
        weights = {"L1": 0.4, "L2": 0.3, "L3": 0.2, "L4": 0.1}
        weighted_cov = sum(weights[L] * layer_cov.get(L, 0.0) for L in layers)

        # 低 L1 罚分
        penalty = 0.7 if layer_cov.get("L1", 0.0) < 0.3 else 1.0
        layered_score = max(0.0, min(1.0, float(weighted_cov) * penalty))

        # 结合纯度密度（稳定处理）
        overall = layered_score * (0.6 + 0.4 * weighted_density) * (0.9 + 0.1 * purity)
        overall = max(0.0, min(1.0, overall)) * 100.0

        return ScoringResult(
            overall_score=overall,
            layer_coverage=layer_cov,
            weighted_density=weighted_density,
            coverage=coverage,
            density=density,
            purity=purity,
            mentions=int(total_mentions),
            unique_terms=int(unique),
            tokens=int(total_tokens),
        )


__all__ = ["SemanticScorer", "ScoringResult"]
