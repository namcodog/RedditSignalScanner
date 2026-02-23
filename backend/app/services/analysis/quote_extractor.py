from __future__ import annotations

"""
QuoteExtractor: 从痛点数据中抽取高质量用户引言。

设计要点（对应 spec tasks 1.4/1.5）：
- 输入为 pain point 列表（与分析引擎输出结构兼容）
- 候选来源：user_examples、example_posts.content、description
- 清洗：移除 URL、代码块、markdown 引用、@提及，多空格合并
- 句子切分：按 . ! ? 以及中文 。！？ 分句
- 过滤：仅保留长度 [50, 150] 的句子
- 评分：加权合成 0..1（情感强度 0.4 + 关键词相关度 0.4 + 情绪标记 0.2）
  * 情感强度：基于 signal_keywords.yaml 的负面词出现次数
  * 关键词相关度：description 提取的简单关键词在句子中的命中率
  * 情绪标记：包含 '!' 记为 1.0，包含 '?' 记为 0.7，同时存在记为 1.0
- 排序：按分数降序，去重后返回前 N 条
"""

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from app.services.analysis.text_cleaner import clean_text
from app.services.analysis.signal_lexicon import get_signal_lexicon


_AT_MENTION_RE = re.compile(r"@[A-Za-z0-9_]+")
_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|")  # 兼容中文/英文断句及换行
_TOKEN_RE = re.compile(r"[a-zA-Z]{4,}")


@dataclass(slots=True)
class QuoteResult:
    text: str
    score: float
    sentiment: float
    relevance: float
    length: int
    source: str  # "user_examples" | "example_posts" | "description"

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "score": round(self.score, 3),
            "sentiment": round(self.sentiment, 3),
            "relevance": round(self.relevance, 3),
            "length": self.length,
            "source": self.source,
        }


class QuoteExtractor:
    MIN_LEN = 50
    MAX_LEN = 150

    # 权重：情感 0.4 + 相关度 0.4 + 情绪标记 0.2
    W_SENTIMENT = 0.4
    W_RELEVANCE = 0.4
    W_EMOTION = 0.2

    def extract_from_pain_points(
        self,
        pain_points: Sequence[Mapping[str, object]],
        *,
        quotes_per_pain: int = 2,
    ) -> list[dict[str, object]]:
        """对每个痛点抽取 0-2 条代表性引言。

        返回结构：[{"description": str, "quotes": [QuoteResult.to_dict(), ...]}]
        """
        results: list[dict[str, object]] = []
        for item in pain_points:
            description = str(item.get("description") or "").strip()
            keywords = self._extract_keywords(description)

            candidates: list[QuoteResult] = []
            # user_examples: list[str]
            for sent in self._iter_sentences(_iter_user_examples(item)):
                qr = self._build_scored_quote(sent, keywords, source="user_examples")
                if qr is not None:
                    candidates.append(qr)

            # example_posts: list[{content: str}]
            for sent in self._iter_sentences(_iter_post_contents(item)):
                qr = self._build_scored_quote(sent, keywords, source="example_posts")
                if qr is not None:
                    candidates.append(qr)

            # description 兜底
            for sent in self._iter_sentences([description]):
                qr = self._build_scored_quote(sent, keywords, source="description")
                if qr is not None:
                    candidates.append(qr)

            top = self._rank_candidates(candidates, k=max(0, int(quotes_per_pain)))
            results.append({
                "description": description,
                "quotes": [q.to_dict() for q in top],
            })

        return results

    # ---------------- internal helpers ----------------

    def _rank_candidates(self, items: Sequence[QuoteResult], *, k: int) -> list[QuoteResult]:
        seen: set[str] = set()
        deduped: list[QuoteResult] = []
        for it in sorted(items, key=lambda x: (-x.score, -x.length)):
            key = it.text.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
            if len(deduped) >= k:
                break
        return deduped

    def _build_scored_quote(
        self, sentence: str, keywords: set[str], *, source: str
    ) -> QuoteResult | None:
        raw = self._clean_quote(sentence)
        if not raw:
            return None
        L = len(raw)
        if L < self.MIN_LEN or L > self.MAX_LEN:
            return None
        sentiment, relevance, emo = self._calculate_quote_score(raw, keywords)
        score = (
            self.W_SENTIMENT * sentiment
            + self.W_RELEVANCE * relevance
            + self.W_EMOTION * emo
        )
        score = max(0.0, min(1.0, score))
        return QuoteResult(text=raw, score=score, sentiment=sentiment, relevance=relevance, length=L, source=source)

    def _clean_quote(self, text: str) -> str:
        text = clean_text(text or "")
        if not text:
            return ""
        text = _AT_MENTION_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _calculate_quote_score(self, text: str, keywords: set[str]) -> tuple[float, float, float]:
        """返回 (sentiment, relevance, emotion) 三个 0..1 分量。

        - 情感：负面术语命中次数转为强度（痛点语境中更能代表用户情绪）
        - 相关：description 关键词在句子中的覆盖率
        - 情绪：感叹/问号标记
        """
        lower = text.lower()
        neg_terms: Iterable[str] = get_signal_lexicon().negative_terms
        neg_hits = 0
        for term in neg_terms:
            if term in lower:
                neg_hits += 1
                if neg_hits >= 4:
                    break
        # 0..1：>=3 命中近似饱和
        sentiment = min(1.0, neg_hits / 3.0)

        rel = 0.0
        if keywords:
            matched = sum(1 for kw in keywords if kw in lower)
            rel = max(0.0, min(1.0, matched / max(1, len(keywords))))

        has_excl = "!" in text or "！" in text
        has_qm = "?" in text or "？" in text
        if has_excl and has_qm:
            emo = 1.0
        elif has_excl:
            emo = 1.0
        elif has_qm:
            emo = 0.7
        else:
            emo = 0.0

        return sentiment, rel, emo

    def _iter_sentences(self, texts: Iterable[str]) -> Iterable[str]:
        for block in texts:
            if not block:
                continue
            # 允许换行，统一清洗再分句
            cleaned = (block or "").replace("\n", " ").strip()
            if not cleaned:
                continue
            parts = re.split(r"(?<=[.!?。！？])\s+|\n", cleaned)
            for part in parts:
                value = part.strip()
                if value:
                    yield value

    def _extract_keywords(self, description: str) -> set[str]:
        kws: set[str] = set()
        for m in _TOKEN_RE.findall(description.lower()):
            if len(m) >= 4:
                kws.add(m)
        return kws


def _iter_user_examples(item: Mapping[str, object]) -> Iterable[str]:
    raw = item.get("user_examples") or []
    if isinstance(raw, Sequence):
        for x in raw:
            s = str(x or "").strip()
            if s:
                yield s


def _iter_post_contents(item: Mapping[str, object]) -> Iterable[str]:
    raw = item.get("example_posts") or []
    if isinstance(raw, Sequence):
        for x in raw:
            if not isinstance(x, Mapping):
                continue
            s = str(x.get("content") or "").strip()
            if s:
                yield s


__all__ = ["QuoteExtractor", "QuoteResult"]
