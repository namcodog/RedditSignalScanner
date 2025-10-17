from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(slots=True)
class PainPointSignal:
    description: str
    frequency: int
    sentiment: float
    keywords: List[str]
    source_posts: List[str]
    relevance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "frequency": self.frequency,
            "sentiment_score": round(self.sentiment, 2),
            "example_posts": self.source_posts[:3],
        }


@dataclass(slots=True)
class CompetitorSignal:
    name: str
    mention_count: int
    sentiment: float
    context_snippets: List[str]
    source_posts: List[str]
    relevance: float

    def to_dict(self) -> Dict[str, Any]:
        sentiment_label = "positive"
        if self.sentiment < -0.15:
            sentiment_label = "negative"
        elif abs(self.sentiment) <= 0.15:
            sentiment_label = "mixed"

        strengths = ["社区讨论热度高"]
        weaknesses = ["等待更多反馈细节"]
        if sentiment_label == "negative":
            strengths = ["行业认知度高"]
            weaknesses = ["用户反馈偏负面"]
        elif sentiment_label == "positive":
            strengths = ["用户反馈积极", "社区认可度高"]
            weaknesses = ["需要继续观察长期表现"]

        return {
            "name": self.name,
            "mentions": self.mention_count,
            "sentiment": sentiment_label,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }


@dataclass(slots=True)
class OpportunitySignal:
    description: str
    demand_score: float
    unmet_need: str
    potential_users: int
    source_posts: List[str]
    relevance: float
    keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "relevance_score": round(self.relevance, 2),
            "potential_users": f"约{self.potential_users}个潜在团队",
            "key_insights": self.keywords[:4],
            "source_posts": self.source_posts[:3],
        }


@dataclass(slots=True)
class BusinessSignals:
    pain_points: List[PainPointSignal]
    competitors: List[CompetitorSignal]
    opportunities: List[OpportunitySignal]


class SignalExtractor:
    """
    Lightweight signal extraction heuristics aligned with PRD/PRD-03 Step 3.

    The goal is to provide deterministic-yet-believable signals for automated
    tests while keeping the implementation free of heavyweight NLP models.
    """

    _NEGATIVE_TERMS = {
        # 英文痛点词汇
        "slow",
        "confusing",
        "expensive",
        "complex",
        "bug",
        "broken",
        "issue",
        "problem",
        "frustrating",
        "annoying",
        "difficult",
        "hate",
        "can't stand",
        "can't believe",
        "painful",
        "unreliable",
        "doesn't work",
        "terrible",
        "awful",
        "horrible",
        "useless",
        "waste",
        "sucks",
        "bad",
        "poor",
        "lacking",
        "missing",
        "limited",
        "clunky",
        "outdated",
        "buggy",
        "crashes",
        "fails",
        "error",
        "wrong",
        "hard",
        "complicated",
        "tedious",
        "time-consuming",
        "inefficient",
        # 情感词汇
        "disappointed",
        "frustrated",
        "angry",
        "upset",
        "annoyed",
        "irritated",
        # 功能缺失
        "no way to",
        "can't",
        "unable to",
        "impossible to",
        "doesn't support",
        "lacks",
        "missing feature",
        "not working",
        "stopped working",
    }

    _PAIN_PATTERNS = [
        re.compile(r"\b(i\s+(?:hate|can't stand|dislike)\s+.+)", re.IGNORECASE),
        re.compile(
            r"\b(.+?\s+is\s+(?:too\s+)?(?:slow|broken|unreliable|expensive|bad|terrible))",
            re.IGNORECASE,
        ),
        re.compile(r"\b(struggle[s]? to\s+.+)", re.IGNORECASE),
        re.compile(r"\b(problem[s]? with\s+.+)", re.IGNORECASE),
        re.compile(r"\b(why is .+? so .+)", re.IGNORECASE),
        re.compile(r"\b(can't believe .+)", re.IGNORECASE),
        re.compile(r"\b(.+ doesn't work)", re.IGNORECASE),
        re.compile(r"\b(frustrated with\s+.+)", re.IGNORECASE),
        re.compile(r"\b(tired of\s+.+)", re.IGNORECASE),
        re.compile(r"\b(sick of\s+.+)", re.IGNORECASE),
        re.compile(r"\b(no way to\s+.+)", re.IGNORECASE),
        re.compile(r"\b(can't figure out\s+.+)", re.IGNORECASE),
    ]

    _OPPORTUNITY_CUES = [
        # 需求表达
        "looking for",
        "need a",
        "need an",
        "need to",
        "searching for",
        "want a",
        "want an",
        # 愿意付费
        "would pay for",
        "willing to pay",
        "pay for",
        "subscription",
        # 期望功能
        "would love",
        "wish there was",
        "wish I could",
        "if only",
        "hope for",
        # 缺失功能
        "missing",
        "lacks",
        "doesn't have",
        "no support for",
        # 替代方案
        "alternative to",
        "better than",
        "replacement for",
        # 推荐请求
        "recommend",
        "suggestion",
        "any tools",
        "best tool",
        "what do you use",
    ]

    _URGENCY_TERMS = {
        "urgent",
        "now",
        "immediately",
        "asap",
        "today",
        "right now",
        "desperately",
        "critical",
        "must have",
        "essential",
        "required",
        "necessary",
    }

    _COMPETITOR_CUES = (
        " vs ",
        " versus ",
        "alternative to",
        "instead of",
        "compared to",
        "better than",
        "switching from",
        "migrating from",
        "replacing",
        "vs.",
        "or",
        " v ",
    )

    _MAX_PAIN_POINTS = 15  # 增加到 15 个
    _MAX_COMPETITORS = 12  # 增加到 12 个
    _MAX_OPPORTUNITIES = 10  # 增加到 10 个

    _PRODUCT_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\b")
    _PRODUCT_WITH_SUFFIX_PATTERN = re.compile(
        r"\b([A-Z][A-Za-z0-9]+(?:\s+(?:App|Tool|Platform|Suite|AI|API)))\b"
    )
    _DOMAIN_PATTERN = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9-]+\.[a-z]{2,})\b")

    def extract(
        self,
        posts: Sequence[Dict[str, Any]],
        keywords: Sequence[str],
        *,
        max_pain_points: int | None = None,
        max_competitors: int | None = None,
        max_opportunities: int | None = None,
    ) -> BusinessSignals:
        normalized_posts = list(self._normalize_posts(posts))
        keyword_set = {kw.lower() for kw in keywords if kw}

        pain_points = self._extract_pain_points(normalized_posts, keyword_set)
        competitors = self._extract_competitors(normalized_posts)
        opportunities = self._extract_opportunities(normalized_posts, keyword_set)

        return BusinessSignals(
            pain_points=self._rank_pain_points(
                pain_points, max_pain_points or self._MAX_PAIN_POINTS
            ),
            competitors=self._rank_competitors(
                competitors, max_competitors or self._MAX_COMPETITORS
            ),
            opportunities=self._rank_opportunities(
                opportunities, max_opportunities or self._MAX_OPPORTUNITIES
            ),
        )

    def _normalize_posts(
        self, posts: Sequence[Dict[str, Any]]
    ) -> Iterable[Dict[str, Any]]:
        for post in posts:
            text = f"{post.get('title', '')} {post.get('summary', post.get('selftext', ''))}".strip()
            if not text:
                continue
            yield {
                "id": str(post.get("id", "")),
                "text": text,
                "text_lower": text.lower(),
                "score": float(post.get("score", 0) or 0),
                "num_comments": int(post.get("num_comments", 0) or 0),
            }

    def _extract_pain_points(
        self,
        posts: Sequence[Dict[str, Any]],
        keyword_set: set[str],
    ) -> List[PainPointSignal]:
        aggregates: Dict[str, Dict[str, Any]] = {}

        for post in posts:
            sentences = self._split_sentences(post["text"])
            for sentence in sentences:
                if not sentence or len(sentence) < 10:  # 过滤太短的句子
                    continue
                sentence_lower = sentence.lower()

                # 检查是否包含负面词汇
                matched_terms = [
                    term for term in self._NEGATIVE_TERMS if term in sentence_lower
                ]

                # 或者匹配痛点模式
                pattern_matched = any(
                    pattern.search(sentence) for pattern in self._PAIN_PATTERNS
                )

                if not matched_terms and not pattern_matched:
                    continue

                # 检查是否与关键词相关
                matched_keywords = [kw for kw in keyword_set if kw in sentence_lower]

                # 提取痛点描述
                description = self._extract_pain_description(sentence, matched_terms)
                if len(description) < 15:  # 过滤太短的描述
                    continue

                key = description.lower()[:100]  # 使用前100个字符作为key，避免重复

                # 计算情感分数（更细粒度）
                sentiment = -0.3  # 基础负面分数
                if matched_terms:
                    sentiment = max(-1.0, -0.3 - 0.15 * min(len(matched_terms), 5))
                if "hate" in sentence_lower or "terrible" in sentence_lower:
                    sentiment = min(sentiment - 0.2, -0.9)
                if "can't" in sentence_lower or "unable" in sentence_lower:
                    sentiment = min(sentiment - 0.1, -0.8)

                entry = aggregates.setdefault(
                    key,
                    {
                        "description": description,
                        "keywords": set(),
                        "source_posts": set(),
                        "frequency": 0,
                        "sentiment_total": 0.0,
                        "max_engagement": 0.0,
                    },
                )
                entry["frequency"] += 1
                entry["sentiment_total"] += sentiment
                entry["source_posts"].add(post["id"])
                entry["max_engagement"] = max(
                    entry["max_engagement"], post["score"] + post["num_comments"] * 0.5
                )
                for keyword in matched_keywords:
                    entry["keywords"].add(keyword)

        signals: List[PainPointSignal] = []
        for entry in aggregates.values():
            frequency = entry["frequency"]
            sentiment_avg = entry["sentiment_total"] / max(frequency, 1)
            keyword_bonus = min(len(entry["keywords"]) / 3.0, 1.0)
            engagement_score = min(entry["max_engagement"] / 80.0, 1.0)

            # 改进相关性计算：频率权重更高
            relevance = (
                min(frequency / 3.0, 1.0) * 0.50
                + abs(sentiment_avg) * 0.30  # 频率权重提高到 50%
                + keyword_bonus * 0.15  # 情感强度 30%
                + engagement_score * 0.05  # 关键词匹配 15%  # 互动度 5%
            )

            signals.append(
                PainPointSignal(
                    description=entry["description"],
                    frequency=frequency,
                    sentiment=sentiment_avg,
                    keywords=sorted(entry["keywords"]),
                    source_posts=sorted(entry["source_posts"]),
                    relevance=relevance,
                )
            )
        return signals

    def _extract_competitors(
        self, posts: Sequence[Dict[str, Any]]
    ) -> List[CompetitorSignal]:
        aggregates: Dict[str, Dict[str, Any]] = {}

        for post in posts:
            text = post["text"]
            sentences = self._split_sentences(text)

            for sentence in sentences:
                if not sentence or len(sentence) < 15:
                    continue
                sentence_lower = sentence.lower()

                # 检查是否包含竞品线索
                has_competitor_cue = any(
                    cue in sentence_lower for cue in self._COMPETITOR_CUES
                )

                # 提取产品名称
                product_names = self._extract_product_names(sentence)
                if not product_names:
                    continue

                # 如果没有明确的竞品线索，但提到了多个产品，也认为是竞品比较
                if not has_competitor_cue and len(product_names) < 2:
                    continue

                # 计算情感分数
                negative_count = sum(
                    1 for term in self._NEGATIVE_TERMS if term in sentence_lower
                )
                if negative_count > 0:
                    sentiment = max(-0.8, -0.2 - 0.15 * negative_count)
                elif any(
                    word in sentence_lower
                    for word in ["better", "prefer", "love", "great", "best"]
                ):
                    sentiment = 0.4
                else:
                    sentiment = 0.1

                snippet = sentence.strip()[:200]

                for name in product_names:
                    # 过滤常见的非产品词
                    if name.lower() in {
                        "reddit",
                        "google",
                        "facebook",
                        "twitter",
                        "youtube",
                    }:
                        continue

                    entry = aggregates.setdefault(
                        name,
                        {
                            "name": name,
                            "mention_count": 0,
                            "sentiment_total": 0.0,
                            "contexts": [],
                            "source_posts": set(),
                        },
                    )
                    entry["mention_count"] += 1
                    entry["sentiment_total"] += sentiment
                    if len(entry["contexts"]) < 5:  # 增加到 5 个上下文
                        entry["contexts"].append(snippet)
                    entry["source_posts"].add(post["id"])

        signals: List[CompetitorSignal] = []
        for entry in aggregates.values():
            mention_count = entry["mention_count"]
            if mention_count < 1:  # 至少提到 1 次
                continue

            sentiment_avg = entry["sentiment_total"] / max(mention_count, 1)
            diversity_bonus = min(len(entry["contexts"]) / 4.0, 1.0)

            # 改进相关性计算
            relevance = (
                min(mention_count / 3.0, 1.0) * 0.60
                + abs(sentiment_avg) * 0.25  # 提及次数权重 60%
                + diversity_bonus * 0.15  # 情感强度 25%  # 上下文多样性 15%
            )

            signals.append(
                CompetitorSignal(
                    name=entry["name"],
                    mention_count=mention_count,
                    sentiment=sentiment_avg,
                    context_snippets=entry["contexts"],
                    source_posts=sorted(entry["source_posts"]),
                    relevance=relevance,
                )
            )
        return signals

    def _extract_opportunities(
        self,
        posts: Sequence[Dict[str, Any]],
        keyword_set: set[str],
    ) -> List[OpportunitySignal]:
        aggregates: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "description": "",
                "demand": 0,
                "urgency": 0.0,
                "score_total": 0.0,
                "source_posts": set(),
                "keywords": set(),
            }
        )

        for post in posts:
            sentences = self._split_sentences(post["text"])
            for sentence in sentences:
                if not sentence or len(sentence) < 15:
                    continue
                sentence_lower = sentence.lower()

                # 检查是否包含机会线索
                cue = next(
                    (c for c in self._OPPORTUNITY_CUES if c in sentence_lower), None
                )
                if cue is None:
                    continue

                # 提取机会描述
                description = self._extract_opportunity_description(sentence, cue)
                if len(description) < 20:  # 过滤太短的描述
                    continue

                key = description.lower()[:100]  # 使用前100个字符作为key

                entry = aggregates[key]
                entry["description"] = description
                entry["demand"] += 1
                entry["score_total"] += post["score"]
                entry["source_posts"].add(post["id"])

                # 计算紧迫性
                if any(term in sentence_lower for term in self._URGENCY_TERMS):
                    entry["urgency"] += 1.5  # 紧急词汇权重更高
                elif "need" in sentence_lower or "must" in sentence_lower:
                    entry["urgency"] += 1.0
                elif "would" in sentence_lower or "wish" in sentence_lower:
                    entry["urgency"] += 0.5

                # 提取关键词
                if keyword_set:
                    words = set(sentence_lower.split())
                    matched_keywords = keyword_set.intersection(words)
                    entry["keywords"].update(matched_keywords)

                # 检查是否提到付费意愿
                if any(
                    word in sentence_lower
                    for word in ["pay", "subscription", "pricing", "cost"]
                ):
                    entry["urgency"] += 0.8

        signals: List[OpportunitySignal] = []
        for entry in aggregates.values():
            frequency = entry["demand"]
            if frequency < 1:  # 至少出现 1 次
                continue

            demand_score = min(frequency / 3.0, 1.0)  # 降低阈值
            urgency = min(entry["urgency"] / max(frequency, 1), 1.5)  # 允许超过 1.0
            avg_score = entry["score_total"] / max(frequency, 1)
            market_projection = min(avg_score / 60.0, 1.0)  # 降低阈值
            keyword_bonus = min(len(entry["keywords"]) / 3.0, 1.0)

            # 改进相关性计算
            relevance = (
                demand_score * 0.35
                + min(urgency, 1.0) * 0.30  # 需求频率 35%
                + market_projection * 0.20  # 紧迫性 30%
                + keyword_bonus * 0.15  # 市场潜力 20%  # 关键词匹配 15%
            )

            potential_users = int(
                100 + frequency * 50 + avg_score * 2.0 + len(entry["keywords"]) * 20
            )

            signals.append(
                OpportunitySignal(
                    description=entry["description"],
                    demand_score=demand_score,
                    unmet_need=entry["description"],
                    potential_users=potential_users,
                    source_posts=sorted(entry["source_posts"]),
                    relevance=relevance,
                    keywords=sorted(entry["keywords"]),
                )
            )
        return signals

    def _rank_pain_points(
        self, signals: List[PainPointSignal], limit: int
    ) -> List[PainPointSignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[
            :limit
        ]

    def _rank_competitors(
        self, signals: List[CompetitorSignal], limit: int
    ) -> List[CompetitorSignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[
            :limit
        ]

    def _rank_opportunities(
        self, signals: List[OpportunitySignal], limit: int
    ) -> List[OpportunitySignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[
            :limit
        ]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return [
            segment.strip()
            for segment in re.split(r"[.!?\n]+", text)
            if segment.strip()
        ]

    @staticmethod
    def _extract_pain_description(sentence: str, matched_terms: List[str]) -> str:
        cleaned = sentence.strip()
        for term in matched_terms:
            cleaned = cleaned.replace(term, term)
        return cleaned[:180]

    def _extract_product_names(self, sentence: str) -> List[str]:
        candidates = {
            match.group(1).strip() for match in self._PRODUCT_PATTERN.finditer(sentence)
        }
        for match in self._PRODUCT_WITH_SUFFIX_PATTERN.finditer(sentence):
            candidates.add(match.group(1).strip())

        domains = {
            match.group(1).lower() for match in self._DOMAIN_PATTERN.finditer(sentence)
        }
        for domain in domains:
            base = domain.split(".")[0]
            if base:
                candidates.add(base.title())

        filtered = {
            name for name in candidates if len(name) >= 3 and not name.isupper()
        }
        return sorted(filtered)

    @staticmethod
    def _extract_opportunity_description(sentence: str, cue: str) -> str:
        lower = sentence.lower()
        start = lower.find(cue)
        if start == -1:
            return sentence.strip()[:180]
        description = sentence[start:].strip()
        if len(description) < 12:
            return sentence.strip()[:180]
        return description[:200]


__all__ = [
    "BusinessSignals",
    "CompetitorSignal",
    "OpportunitySignal",
    "PainPointSignal",
    "SignalExtractor",
]
