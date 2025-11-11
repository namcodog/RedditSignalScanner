"""
Hybrid Matcher - 支持 exact/phrase/semantic 三种匹配策略

根据词库中的 precision_tag 自动选择匹配方式：
- exact: 完全匹配（品牌名、平台名）
- phrase: 短语匹配（功能词、痛点短语）
- semantic: 语义相似度匹配（向量近邻）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

# 可选：如果需要语义匹配，可以引入 sentence-transformers
# from sentence_transformers import SentenceTransformer
# import numpy as np


@dataclass
class Term:
    """词条"""
    canonical: str
    aliases: List[str]
    precision_tag: str  # exact | phrase | semantic
    category: str  # brands | features | pain_points
    weight: float = 1.0


@dataclass
class MatchResult:
    """匹配结果"""
    term: str
    canonical: str
    category: str
    count: int
    positions: List[int]  # 匹配位置（字符索引）
    match_type: str  # exact | phrase | semantic


class HybridMatcher:
    """混合匹配器"""
    
    def __init__(self, terms: List[Term], *, enable_semantic: bool = False):
        """
        Args:
            terms: 词条列表
            enable_semantic: 是否启用语义匹配（需要加载模型，较慢）
        """
        self.terms = terms
        self.enable_semantic = enable_semantic
        
        # 按 precision_tag 分组
        self.exact_terms: List[Term] = []
        self.phrase_terms: List[Term] = []
        self.semantic_terms: List[Term] = []
        
        for term in terms:
            if term.precision_tag == "exact":
                self.exact_terms.append(term)
            elif term.precision_tag == "phrase":
                self.phrase_terms.append(term)
            elif term.precision_tag == "semantic":
                self.semantic_terms.append(term)
        
        # 预编译正则
        self._exact_patterns = self._compile_exact_patterns(self.exact_terms)
        self._phrase_patterns = self._compile_phrase_patterns(self.phrase_terms)
        
        # 语义模型（可选）
        self._semantic_model = None
        if enable_semantic and self.semantic_terms:
            try:
                from sentence_transformers import SentenceTransformer
                self._semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("⚠️  sentence-transformers not installed, semantic matching disabled")
    
    def _compile_exact_patterns(self, terms: List[Term]) -> Dict[str, Tuple[Term, re.Pattern]]:
        """
        编译 exact 匹配模式
        
        exact 匹配规则：
        - 完全匹配词边界
        - 不区分大小写
        - 支持别名
        """
        patterns = {}
        for term in terms:
            all_variants = [term.canonical] + term.aliases
            for variant in all_variants:
                # 转义特殊字符
                escaped = re.escape(variant)
                # 词边界匹配
                pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
                patterns[variant] = (term, pattern)
        return patterns
    
    def _compile_phrase_patterns(self, terms: List[Term]) -> Dict[str, Tuple[Term, re.Pattern]]:
        """
        编译 phrase 匹配模式
        
        phrase 匹配规则：
        - 短语匹配（可以跨词）
        - 不区分大小写
        - 支持别名
        """
        patterns = {}
        for term in terms:
            all_variants = [term.canonical] + term.aliases
            for variant in all_variants:
                # 转义特殊字符
                escaped = re.escape(variant)
                # 不要求词边界（允许作为子串）
                pattern = re.compile(escaped, re.IGNORECASE)
                patterns[variant] = (term, pattern)
        return patterns
    
    def match_text(self, text: str) -> List[MatchResult]:
        """
        匹配文本
        
        Args:
            text: 待匹配文本
        
        Returns:
            匹配结果列表
        """
        results = []
        
        # 1. exact 匹配
        for variant, (term, pattern) in self._exact_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                results.append(MatchResult(
                    term=variant,
                    canonical=term.canonical,
                    category=term.category,
                    count=len(matches),
                    positions=[m.start() for m in matches],
                    match_type="exact",
                ))
        
        # 2. phrase 匹配
        for variant, (term, pattern) in self._phrase_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                results.append(MatchResult(
                    term=variant,
                    canonical=term.canonical,
                    category=term.category,
                    count=len(matches),
                    positions=[m.start() for m in matches],
                    match_type="phrase",
                ))
        
        # 3. semantic 匹配（可选）
        if self.enable_semantic and self._semantic_model and self.semantic_terms:
            semantic_results = self._match_semantic(text)
            results.extend(semantic_results)
        
        return results
    
    def _match_semantic(self, text: str, threshold: float = 0.75) -> List[MatchResult]:
        """
        语义匹配
        
        Args:
            text: 待匹配文本
            threshold: 相似度阈值
        
        Returns:
            匹配结果列表
        """
        if not self._semantic_model:
            return []
        
        results = []
        
        # 对文本分句（简单按句号分割）
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return []
        
        # 编码句子
        sentence_embeddings = self._semantic_model.encode(sentences)
        
        # 对每个 semantic term 计算相似度
        for term in self.semantic_terms:
            all_variants = [term.canonical] + term.aliases
            term_embeddings = self._semantic_model.encode(all_variants)
            
            # 计算相似度矩阵
            import numpy as np
            similarities = np.dot(sentence_embeddings, term_embeddings.T)
            
            # 找到超过阈值的匹配
            matched_sentences = []
            for i, sent_sims in enumerate(similarities):
                max_sim = sent_sims.max()
                if max_sim >= threshold:
                    matched_sentences.append(i)
            
            if matched_sentences:
                results.append(MatchResult(
                    term=term.canonical,
                    canonical=term.canonical,
                    category=term.category,
                    count=len(matched_sentences),
                    positions=[],  # 语义匹配没有精确位置
                    match_type="semantic",
                ))
        
        return results
    
    def aggregate_by_category(self, results: List[MatchResult]) -> Dict[str, int]:
        """
        按类别聚合匹配结果
        
        Args:
            results: 匹配结果列表
        
        Returns:
            {category: total_count}
        """
        aggregated = {}
        for result in results:
            category = result.category
            aggregated[category] = aggregated.get(category, 0) + result.count
        return aggregated
    
    def aggregate_by_canonical(self, results: List[MatchResult]) -> Dict[str, int]:
        """
        按规范名聚合匹配结果（去重别名）
        
        Args:
            results: 匹配结果列表
        
        Returns:
            {canonical: total_count}
        """
        aggregated = {}
        for result in results:
            canonical = result.canonical
            aggregated[canonical] = aggregated.get(canonical, 0) + result.count
        return aggregated


# ============================================
# 使用示例
# ============================================

def example_usage():
    """使用示例"""
    
    # 1. 定义词条
    terms = [
        Term(
            canonical="Amazon",
            aliases=["AMZ", "amazon.com"],
            precision_tag="exact",
            category="brands",
            weight=1.5,
        ),
        Term(
            canonical="dropshipping",
            aliases=["dropship", "drop shipping"],
            precision_tag="phrase",
            category="features",
            weight=1.0,
        ),
        Term(
            canonical="saturated market",
            aliases=["oversaturated", "too competitive"],
            precision_tag="semantic",
            category="pain_points",
            weight=1.2,
        ),
    ]
    
    # 2. 创建匹配器
    matcher = HybridMatcher(terms, enable_semantic=False)
    
    # 3. 匹配文本
    text = """
    I'm selling on Amazon and doing dropshipping.
    The market is oversaturated and very competitive.
    AMZ fees are too high.
    """
    
    results = matcher.match_text(text)
    
    # 4. 查看结果
    print("=== Match Results ===")
    for r in results:
        print(f"{r.canonical} ({r.category}): {r.count} matches, type={r.match_type}")
    
    # 5. 聚合
    by_category = matcher.aggregate_by_category(results)
    print("\n=== By Category ===")
    for cat, count in by_category.items():
        print(f"{cat}: {count}")
    
    by_canonical = matcher.aggregate_by_canonical(results)
    print("\n=== By Canonical ===")
    for canonical, count in by_canonical.items():
        print(f"{canonical}: {count}")


if __name__ == "__main__":
    example_usage()

