"""Opportunity scoring utilities based on configurable keyword rules.

Phase 5.2: Added score_with_needs() for Human Needs Graph integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.services.analysis.scoring_rules import (
    KeywordRule,
    NegationRule,
    ScoringRules,
    ScoringRulesLoader,
)
from app.services.analysis.template_matcher import TemplateMatcher

logger = logging.getLogger(__name__)

# Need category weights (User Confirmed: Efficiency = 2.5 highest)
NEED_WEIGHTS = {
    "Survival": 1.5,
    "Efficiency": 2.5,  # User confirmed: "找工具" = 直接付费意愿
    "Growth": 1.2,
    "Belonging": 0.5,
    "Aesthetic": 0.5,
}

# Dual-label bonus when primary + secondary form high-value combo
DUAL_LABEL_BONUS = 0.1


@dataclass
class ScoringResult:
    base_score: float
    positive_hits: list[str]
    negative_hits: list[str]
    negated: bool
    template_positive: list[str]
    template_negative: list[str]
    template_boost: float
    template_penalty: float


@dataclass
class NeedEnrichedScore:
    """Phase 5.2: Need-aware opportunity score."""
    
    final_score: float
    intent_score: float  # Original keyword-based score
    need_score: float  # Score from L1 categories
    sentiment_modifier: float
    dual_label_bonus: float
    need_breakdown: Dict[str, int] = field(default_factory=dict)  # {category: count}
    avg_sentiment: float = 0.0
    post_count: int = 0


class OpportunityScorer:
    """Compute opportunity scores leveraging positive/negative keyword rules."""

    def __init__(
        self,
        loader: ScoringRulesLoader | None = None,
        template_matcher: TemplateMatcher | None = None,
    ) -> None:
        self._loader = loader or ScoringRulesLoader()
        self._rules = self._loader.load()
        self._template_matcher = template_matcher or TemplateMatcher()
        self._need_weights = NEED_WEIGHTS
        self._dual_label_bonus = DUAL_LABEL_BONUS
        self._refresh_need_weights()

    def refresh(self) -> None:
        """Force reload of rule configuration."""
        self._rules = self._loader.load()
        self._template_matcher.refresh()
        self._refresh_need_weights()

    def _refresh_need_weights(self) -> None:
        weights = getattr(self._rules, "need_weights", None)
        if weights:
            self._need_weights = dict(weights)
        else:
            self._need_weights = NEED_WEIGHTS
        dual_bonus = getattr(self._rules, "dual_label_bonus", None)
        if dual_bonus is not None:
            self._dual_label_bonus = float(dual_bonus)
        else:
            self._dual_label_bonus = DUAL_LABEL_BONUS

    def score(self, text: str) -> ScoringResult:
        if not text:
            return ScoringResult(0.0, [], [], False, [], [], 0.0, 0.0)

        self.refresh()
        lowered = text.lower()
        positive_hits = self._collect_hits(lowered, self._rules.positive_keywords)
        negative_hits = self._collect_hits(lowered, self._rules.negative_keywords)
        negated = self._has_negation(lowered, self._rules.negation_patterns)

        template_result = self._template_matcher.match(lowered)

        base_score = 0.0
        for keyword in positive_hits:
            base_score += self._weight_for(keyword, self._rules.positive_keywords)
        for keyword in negative_hits:
            base_score += self._weight_for(keyword, self._rules.negative_keywords)

        base_score += template_result.boost
        base_score -= template_result.penalty

        if negated:
            base_score = min(base_score, 0.0)

        base_score = max(0.0, min(1.0, base_score))

        # 命中计数回写（仅在规则来自 DB 且有 rule_id 时生效）
        rule_ids = self._loader.get_rule_ids_for_keywords(positive_hits + negative_hits)
        if rule_ids:
            self._loader.increment_hit_counts(rule_ids)

        return ScoringResult(
            base_score,
            positive_hits,
            negative_hits,
            negated,
            template_result.positive_matches,
            template_result.negative_matches,
            template_result.boost,
            template_result.penalty,
        )

    def score_with_needs(
        self,
        post_ids: List[int],
        *,
        intent_score: float = 0.0,
    ) -> NeedEnrichedScore:
        """Phase 5.2: Score posts using Human Needs Graph data.
        
        Queries post_semantic_labels for the given posts and computes a
        need-aware opportunity score using the approved formula:
        
        Raw Need Score = Survival×1.5 + Efficiency×2.5 + Growth×1.2
        Final = Intent×0.25 + NeedScore×0.50 + SentimentMod×0.25
        
        Args:
            post_ids: List of post IDs to score
            intent_score: Pre-computed intent score from keyword matching (0.0-1.0)
            
        Returns:
            NeedEnrichedScore with breakdown and final score
        """
        if not post_ids:
            return NeedEnrichedScore(
                final_score=intent_score * 0.25,
                intent_score=intent_score,
                need_score=0.0,
                sentiment_modifier=0.0,
                dual_label_bonus=0.0,
            )
        
        # Database query for L1 categories
        settings = get_settings()
        db_url = settings.database_url.replace("asyncpg", "psycopg")
        engine = create_engine(db_url, future=True)
        
        sql = text("""
            SELECT 
                l1_category,
                l1_secondary,
                sentiment_score
            FROM post_semantic_labels
            WHERE post_id = ANY(:post_ids)
        """)
        
        with engine.connect() as conn:
            rows = conn.execute(sql, {"post_ids": post_ids}).mappings().all()
        
        if not rows:
            return NeedEnrichedScore(
                final_score=intent_score * 0.25,
                intent_score=intent_score,
                need_score=0.0,
                sentiment_modifier=0.0,
                dual_label_bonus=0.0,
            )
        
        # Count categories
        breakdown: Dict[str, int] = {}
        sentiments: List[float] = []
        dual_bonus_count = 0
        
        for row in rows:
            l1 = str(row.get("l1_category") or "")
            l1_sec = str(row.get("l1_secondary") or "")
            sentiment = row.get("sentiment_score")
            
            if l1:
                breakdown[l1] = breakdown.get(l1, 0) + 1
            
            if sentiment is not None:
                sentiments.append(float(sentiment))
            
            # Dual-label bonus: Survival+Efficiency or Growth+Efficiency
            if l1_sec == "Efficiency" and l1 in ("Survival", "Growth"):
                dual_bonus_count += 1
        
        total = len(rows)
        
        # Calculate weighted need score
        raw_need = 0.0
        for cat, count in breakdown.items():
            weight = self._need_weights.get(cat, 0.0)
            raw_need += (count / total) * weight
        
        # Normalize to 0-1 range (max theoretical = 2.5 for 100% Efficiency)
        need_score = min(1.0, raw_need / 2.5)
        
        # Sentiment modifier
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        if avg_sentiment < -0.3:
            sentiment_mod = 0.15  # Strong pain = bonus
        elif avg_sentiment > 0.2:
            sentiment_mod = 0.05  # Positive = small bonus
        else:
            sentiment_mod = 0.0
        
        # Dual-label bonus
        dual_bonus = (dual_bonus_count / total) * self._dual_label_bonus if total else 0.0
        
        # Final score formula
        final = (
            intent_score * 0.25
            + need_score * 0.50
            + sentiment_mod * 0.25
            + dual_bonus
        )
        final = max(0.0, min(1.0, final))
        
        logger.debug(
            f"score_with_needs: posts={total}, breakdown={breakdown}, "
            f"need={need_score:.3f}, sentiment={avg_sentiment:.2f}, final={final:.3f}"
        )
        
        return NeedEnrichedScore(
            final_score=final,
            intent_score=intent_score,
            need_score=need_score,
            sentiment_modifier=sentiment_mod,
            dual_label_bonus=dual_bonus,
            need_breakdown=breakdown,
            avg_sentiment=avg_sentiment,
            post_count=total,
        )

    @staticmethod
    def _collect_hits(text: str, rules: Sequence[KeywordRule]) -> list[str]:
        hits: list[str] = []
        for rule in rules:
            if rule.keyword and rule.keyword in text:
                hits.append(rule.keyword)
        return hits

    @staticmethod
    def _weight_for(keyword: str, rules: Sequence[KeywordRule]) -> float:
        for rule in rules:
            if rule.keyword == keyword:
                return float(rule.weight)
        return 0.0

    @staticmethod
    def _has_negation(text: str, rules: Sequence[NegationRule]) -> bool:
        for rule in rules:
            if rule.pattern and rule.pattern in text:
                return True
        return False


__all__ = ["OpportunityScorer", "ScoringResult", "NeedEnrichedScore", "NEED_WEIGHTS"]
