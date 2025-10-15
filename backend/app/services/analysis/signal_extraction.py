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
    }
    _PAIN_PATTERNS = [
        re.compile(r"\b(i\s+(?:hate|can't stand)\s+.+)", re.IGNORECASE),
        re.compile(r"\b(.+?\s+is\s+(?:too\s+)?(?:slow|broken|unreliable|expensive))", re.IGNORECASE),
        re.compile(r"\b(struggle[s]? to\s+.+)", re.IGNORECASE),
        re.compile(r"\b(problem[s]? with\s+.+)", re.IGNORECASE),
        re.compile(r"\b(why is .+? so .+)", re.IGNORECASE),
        re.compile(r"\b(can't believe .+)", re.IGNORECASE),
        re.compile(r"\b(.+ doesn't work)", re.IGNORECASE),
    ]
    _OPPORTUNITY_CUES = [
        "looking for",
        "need a",
        "need an",
        "would pay for",
        "would love",
        "missing",
        "wish there was",
        "searching for",
        "want a",
        "want an",
    ]
    _URGENCY_TERMS = {"urgent", "now", "immediately", "asap", "today"}
    _COMPETITOR_CUES = (" vs ", " versus ", "alternative to", "instead of", "compared to")
    _MAX_PAIN_POINTS = 10
    _MAX_COMPETITORS = 8
    _MAX_OPPORTUNITIES = 6

    _PRODUCT_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\b")
    _PRODUCT_WITH_SUFFIX_PATTERN = re.compile(
        r"\b([A-Z][A-Za-z0-9]+(?:\s+(?:App|Tool|Platform|Suite)))\b"
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
            pain_points=self._rank_pain_points(pain_points, max_pain_points or self._MAX_PAIN_POINTS),
            competitors=self._rank_competitors(competitors, max_competitors or self._MAX_COMPETITORS),
            opportunities=self._rank_opportunities(opportunities, max_opportunities or self._MAX_OPPORTUNITIES),
        )

    def _normalize_posts(self, posts: Sequence[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
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
                if not sentence:
                    continue
                sentence_lower = sentence.lower()
                matched_terms = [term for term in self._NEGATIVE_TERMS if term in sentence_lower]
                if not matched_terms:
                    continue

                matched_keywords = [kw for kw in keyword_set if kw in sentence_lower]
                description = self._extract_pain_description(sentence, matched_terms)
                key = description.lower()

                sentiment = max(-1.0, -0.35 - 0.1 * len(matched_terms))

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
                entry["max_engagement"] = max(entry["max_engagement"], post["score"] + post["num_comments"] * 0.5)
                for keyword in matched_keywords:
                    entry["keywords"].add(keyword)

        signals: List[PainPointSignal] = []
        for entry in aggregates.values():
            frequency = entry["frequency"]
            sentiment_avg = entry["sentiment_total"] / max(frequency, 1)
            keyword_bonus = min(len(entry["keywords"]) / 4.0, 1.0)
            engagement_score = min(entry["max_engagement"] / 100.0, 1.0)
            relevance = (min(frequency / 5.0, 1.0) * 0.45) + (abs(sentiment_avg) * 0.35) + ((keyword_bonus + engagement_score) * 0.20)

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

    def _extract_competitors(self, posts: Sequence[Dict[str, Any]]) -> List[CompetitorSignal]:
        aggregates: Dict[str, Dict[str, Any]] = {}

        for post in posts:
            sentences = self._split_sentences(post["text"])
            for sentence in sentences:
                if not sentence:
                    continue
                sentence_lower = sentence.lower()
                if not any(cue in sentence_lower for cue in self._COMPETITOR_CUES):
                    continue

                product_names = self._extract_product_names(sentence)
                if not product_names:
                    continue

                sentiment = -0.3 if any(term in sentence_lower for term in self._NEGATIVE_TERMS) else 0.2
                snippet = sentence.strip()

                for name in product_names:
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
                    if len(entry["contexts"]) < 3:
                        entry["contexts"].append(snippet)
                    entry["source_posts"].add(post["id"])

        signals: List[CompetitorSignal] = []
        for entry in aggregates.values():
            mention_count = entry["mention_count"]
            sentiment_avg = entry["sentiment_total"] / max(mention_count, 1)
            diversity_bonus = min(len(entry["contexts"]) / 3.0, 1.0)
            relevance = (min(mention_count / 5.0, 1.0) * 0.5) + (abs(sentiment_avg) * 0.3) + (diversity_bonus * 0.2)

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
            }
        )

        for post in posts:
            sentences = self._split_sentences(post["text"])
            for sentence in sentences:
                if not sentence:
                    continue
                sentence_lower = sentence.lower()
                cue = next((c for c in self._OPPORTUNITY_CUES if c in sentence_lower), None)
                if cue is None:
                    continue

                description = self._extract_opportunity_description(sentence, cue)
                key = description.lower()

                entry = aggregates[key]
                entry["description"] = description
                entry["demand"] += 1
                entry["score_total"] += post["score"]
                entry["source_posts"].add(post["id"])
                if any(term in sentence_lower for term in self._URGENCY_TERMS):
                    entry["urgency"] += 1.0
                elif "need" in sentence_lower or "would" in sentence_lower:
                    entry["urgency"] += 0.5
                if keyword_set and any(keyword in sentence_lower for keyword in keyword_set):
                    entry.setdefault("keywords", set()).update(keyword_set.intersection(sentence_lower.split()))

        signals: List[OpportunitySignal] = []
        for entry in aggregates.values():
            frequency = entry["demand"]
            demand_score = min(frequency / 5.0, 1.0)
            urgency = min(entry["urgency"] / max(frequency, 1), 1.0)
            avg_score = entry["score_total"] / max(frequency, 1)
            market_projection = min(avg_score / 80.0, 1.0)
            relevance = (demand_score * 0.4) + (urgency * 0.3) + (market_projection * 0.3)
            potential_users = int(80 + frequency * 30 + avg_score * 1.5)

            signals.append(
                OpportunitySignal(
                    description=entry["description"],
                    demand_score=demand_score,
                    unmet_need=entry["description"],
                    potential_users=potential_users,
                    source_posts=sorted(entry["source_posts"]),
                    relevance=relevance,
                    keywords=sorted(entry.get("keywords", set())),
                )
            )
        return signals

    def _rank_pain_points(self, signals: List[PainPointSignal], limit: int) -> List[PainPointSignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[:limit]

    def _rank_competitors(self, signals: List[CompetitorSignal], limit: int) -> List[CompetitorSignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[:limit]

    def _rank_opportunities(self, signals: List[OpportunitySignal], limit: int) -> List[OpportunitySignal]:
        return sorted(signals, key=lambda signal: signal.relevance, reverse=True)[:limit]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return [segment.strip() for segment in re.split(r"[.!?\n]+", text) if segment.strip()]

    @staticmethod
    def _extract_pain_description(sentence: str, matched_terms: List[str]) -> str:
        cleaned = sentence.strip()
        for term in matched_terms:
            cleaned = cleaned.replace(term, term)
        return cleaned[:180]

    def _extract_product_names(self, sentence: str) -> List[str]:
        candidates = {match.group(1).strip() for match in self._PRODUCT_PATTERN.finditer(sentence)}
        for match in self._PRODUCT_WITH_SUFFIX_PATTERN.finditer(sentence):
            candidates.add(match.group(1).strip())

        domains = {match.group(1).lower() for match in self._DOMAIN_PATTERN.finditer(sentence)}
        for domain in domains:
            base = domain.split(".")[0]
            if base:
                candidates.add(base.title())

        filtered = {
            name
            for name in candidates
            if len(name) >= 3
            and not name.isupper()
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
