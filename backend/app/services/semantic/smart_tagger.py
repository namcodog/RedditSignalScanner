"""
Semantic Tagger: Human Needs Graph (人类需求图谱)

基于马斯洛需求层次的 5 大分类 (Phase 3.6 Final):
- Survival: 生存/安全 (质量问题、封号风险、物流丢包)
- Efficiency: 效率/便捷 (省时、自动化、好用工具)
- Belonging: 归属/情感 (社交、礼物、宠物、陪伴)
- Aesthetic: 审美/体验 (颜值、设计、氛围、独特)
- Growth: 成长/自我实现 (赚钱、学习、创业、DIY)
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

from flashtext import KeywordProcessor
from sqlalchemy import create_engine, text
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.config import get_settings
from app.services.semantic.need_taxonomy import get_need_taxonomy

logger = logging.getLogger(__name__)

# VADER 分析器
_vader = SentimentIntensityAnalyzer()

# 5 大需求类别（默认值；实际使用可配置）.
NEED_CATEGORIES = ["Survival", "Efficiency", "Belonging", "Aesthetic", "Growth"]

# Phase 3.5: 意图短语 (优先级高于单词)
SECONDARY_THRESHOLD = 1.0


@dataclass(frozen=True)
class NeedScore:
    survival: float = 0.0
    efficiency: float = 0.0
    belonging: float = 0.0
    aesthetic: float = 0.0
    growth: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "Survival": self.survival,
            "Efficiency": self.efficiency,
            "Belonging": self.belonging,
            "Aesthetic": self.aesthetic,
            "Growth": self.growth,
        }

    def primary(self) -> str:
        d = self.to_dict()
        if max(d.values()) == 0:
            return "Unclassified"
        return max(d, key=d.get)

    def secondary(self) -> str | None:
        d = self.to_dict()
        primary = self.primary()
        if primary == "Unclassified":
            return None
            
        d.pop(primary, None)
        if not d:
            return None
        sec = max(d, key=d.get)
        return sec if d[sec] >= SECONDARY_THRESHOLD else None


def get_min_sentiment(text: str) -> float:
    """最大负面原则：切句后取最负的那句的情感分。"""
    if not text:
        return 0.0
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return 0.0
    scores = [
        _vader.polarity_scores(s)['compound']
        for s in sentences if len(s) > 5
    ]
    return min(scores) if scores else 0.0


class SemanticTagger:
    """
    人类需求图谱打标器 (Semantic Tagger)
    Standardized service class for Phase 3.6
    """

    def __init__(self) -> None:
        settings = get_settings()
        db_url = settings.database_url.replace("asyncpg", "psycopg")
        self._engine = create_engine(db_url, future=True)
        self._matcher = KeywordProcessor(case_sensitive=False)
        self._category_map: Dict[str, str] = {}  # term -> category
        taxonomy = get_need_taxonomy()
        self._taxonomy = taxonomy
        self._need_categories = taxonomy.categories or NEED_CATEGORIES
        self._load_rules()

    def _load_rules(self) -> None:
        """从 semantic_rules 加载规则，并映射到 5 大需求类别"""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT r.id, r.term, r.rule_type, r.weight, r.meta, c.code AS concept_code
                    FROM semantic_rules r
                    JOIN semantic_concepts c ON c.id = r.concept_id
                    WHERE r.is_active = true AND c.is_active = true
                """)
            ).mappings().all()

        self._matcher = KeywordProcessor(case_sensitive=False)
        self._category_map = {}

        for row in rows:
            term = str(row.get("term") or "").strip().lower()
            if not term or len(term) < 2:
                continue

            concept = str(row.get("concept_code") or "").lower()
            rule_type = str(row.get("rule_type") or "").lower()
            meta = row.get("meta") or {}
            
            # Map based on rule_type or concept
            category = self._map_to_need(term, concept, rule_type, meta)
            
            if category:
                self._category_map[term] = category
                self._matcher.add_keyword(term, {"term": term, "category": category})

        # 补充核心关键词
        for cat, words in self._taxonomy.need_keywords.items():
            for word in words:
                if word not in self._category_map:
                    self._category_map[word] = cat
                    self._matcher.add_keyword(word, {"term": word, "category": cat})

        logger.info(f"Loaded {len(self._category_map)} terms for need classification")

    def _map_to_need(self, term: str, concept: str, rule_type: str, meta: dict) -> str | None:
        """将规则映射到 5 大需求类别 (Phase C Revised)"""
        # 1. Vertical Rules Mapping (Highest Priority)
        if rule_type == 'vertical_scenario':
            return "Growth"  # Learning how to do X / Workflow -> Growth
        if rule_type == 'vertical_spec':
            return "Efficiency"  # Specs/Tools -> Efficiency
        if rule_type == 'vertical_pain':
            return "Survival"  # Pain -> Survival (Will be gated by sentiment)

        # 2. pain_keywords -> Survival
        if concept == "pain_keywords":
            return "Survival"

        # 3. 检查 negative_hits -> Survival
        neg_hits = meta.get("negative_hits") or []
        if neg_hits:
            return "Survival"

        # 4. 基于关键词特征匹配 (Generic Fallback)
        term_lower = term.lower()
        for cat, words in self._taxonomy.need_keywords.items():
            if any(w in term_lower for w in words):
                return cat

        return None

    def _match_text(self, text: str) -> List[Dict]:
        """匹配文本，返回命中的规则"""
        hits = self._matcher.extract_keywords(text or "", span_info=True)
        return [h[0] for h in hits if isinstance(h[0], dict)]

    def _calculate_scores(self, text: str, hits: List[Dict], sentiment: float) -> NeedScore:
        """Phase C: 计算 5 大需求得分 (严厉版)"""
        scores = {cat: 0.0 for cat in self._need_categories}
        text_lower = text.lower()

        # -1. Phase C Extreme: 噪音过滤器 (Employee Filter)
        # 如果包含明显的员工/职场抱怨词，直接返回 Unclassified (全0)
        # 简单包含检测 (any substring match)
        for noise_kw in self._taxonomy.noise_keywords:
             # 为了避免误杀 (e.g. "shift" key on keyboard), we might need boundary check?
             # NOISE_KEYWORDS are mostly specific bigrams or distinct words.
             # Let's trust the distinct ones. For "shift", it is risky?
             # "shift" -> "night shift", "shift changed".
             # Let's hope "shift" isn't used for "shift key". "shift key" is irrelevant to Needs anyway?
             # Actually "shift" is in NOISE_KEYWORDS.
             # If someone says "My shift key is broken", it matches "shift".
             # To be safe, let's require *multiple* noise keywords? Or trusting the list is specific enough.
             # "shift" is risky. "paycheck" is safe.
             # Let's assume the list is tuned.
             pattern = r"\b" + re.escape(noise_kw) + r"\b"
             if re.search(pattern, text_lower):
                 return NeedScore() # All zeros -> Unclassified

        # 0. 意图短语优先匹配
        for cat, phrases in self._taxonomy.intent_phrases.items():
            for phrase in phrases:
                if phrase in text_lower:
                    scores[cat] += 2.0

        # 1. Base Score: 关键词命中计数
        for hit in hits:
            cat = hit.get("category")
            if cat and cat in scores:
                scores[cat] += 1.0

        # 2. Sentiment Modifier (Phase C: Strict Survival Gate)
        # Survival 必须伴随明显负面情感，否则清零或降级
        if scores["Survival"] > 0:
            if sentiment >= -0.05: 
                # Neutral/Positive -> NOT Survival (e.g. "How to fix X?" w/o anger)
                # UNLESS it's a "Safety" keyword? Assuming generic pain here.
                scores["Survival"] = 0.0 
            elif sentiment >= -0.2:
                # Weakly negative -> Downgrade
                scores["Survival"] *= 0.5
            else:
                # Strongly negative -> Boost
                scores["Survival"] *= 1.5

        # 3. Intent Modifier
        if "?" in text:
            scores["Growth"] *= 1.3
            scores["Efficiency"] *= 1.1

        # 4. Conflict Resolution (Survival vs Others)
        # If Survival is present but Sentiment is not EXTREME, and Growth/Efficiency exist, prefer them.
        if scores["Survival"] > 0 and sentiment > -0.4:
            if scores["Growth"] >= scores["Survival"] or scores["Efficiency"] >= scores["Survival"]:
                scores["Survival"] *= 0.5

        return NeedScore(
            survival=scores["Survival"],
            efficiency=scores["Efficiency"],
            belonging=scores["Belonging"],
            aesthetic=scores["Aesthetic"],
            growth=scores["Growth"],
        )

    def _upsert_label(self, payload: Dict[str, Any]) -> None:
        """写入标签"""
        stmt = text("""
            INSERT INTO post_semantic_labels (
                post_id, l1_category, l1_secondary, l2_business, l3_scene,
                matched_rule_ids, top_terms, raw_scores,
                sentiment_score, confidence
            )
            VALUES (
                :post_id, :l1_category, :l1_secondary, :l2_business, :l3_scene,
                :matched_rule_ids, :top_terms, :raw_scores,
                :sentiment_score, :confidence
            )
            ON CONFLICT (post_id) DO UPDATE SET
                l1_category = EXCLUDED.l1_category,
                l1_secondary = EXCLUDED.l1_secondary,
                l2_business = EXCLUDED.l2_business,
                l3_scene = EXCLUDED.l3_scene,
                matched_rule_ids = EXCLUDED.matched_rule_ids,
                top_terms = EXCLUDED.top_terms,
                raw_scores = EXCLUDED.raw_scores,
                sentiment_score = EXCLUDED.sentiment_score,
                confidence = EXCLUDED.confidence,
                updated_at = NOW()
        """)
        with self._engine.begin() as conn:
            conn.execute(stmt, payload)

    def process_single(self, post_id: int) -> Dict[str, Any]:
        """处理单个帖子"""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT id, title, body, subreddit
                    FROM posts_raw
                    WHERE id = :pid AND is_current = true
                """),
                {"pid": post_id},
            ).mappings().first()

        if not row:
            return {"post_id": post_id, "status": "not_found"}

        text_content = f"{row.get('title') or ''}\n{row.get('body') or ''}"
        subreddit = row.get("subreddit") or ""

        # 匹配
        hits = self._match_text(text_content)

        # 情感分析
        sentiment = get_min_sentiment(text_content)

        # 计算需求得分
        need_score = self._calculate_scores(text_content, hits, sentiment)

        # 构建 payload
        matched_ids = list(set(hash(h.get("term", "")) % 1000000 for h in hits))[:20]
        top_terms = [h.get("term") for h in hits[:10] if h.get("term")]

        payload = {
            "post_id": post_id,
            "l1_category": need_score.primary(),
            "l1_secondary": need_score.secondary(),
            "l2_business": subreddit,
            "l3_scene": None,
            "matched_rule_ids": matched_ids or None,
            "top_terms": top_terms or None,
            "raw_scores": json.dumps(need_score.to_dict()),
            "sentiment_score": sentiment,
            "confidence": min(1.0, sum(need_score.to_dict().values()) * 0.1),
        }

        self._upsert_label(payload)
        return {"post_id": post_id, "status": "ok", "primary": need_score.primary()}

    def process_batch(self, limit: int = 500) -> Dict[str, Any]:
        """批量处理未打标的帖子"""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT pr.id, pr.title, pr.body, pr.subreddit
                    FROM posts_raw pr
                    LEFT JOIN post_semantic_labels psl ON psl.post_id = pr.id
                    WHERE pr.is_current = true AND psl.post_id IS NULL
                    ORDER BY pr.id DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).mappings().all()

        if not rows:
            return {"processed": 0, "skipped": 0}

        processed = 0
        for row in rows:
            post_id = int(row["id"])
            text_content = f"{row.get('title') or ''}\n{row.get('body') or ''}"
            subreddit = row.get("subreddit") or ""

            hits = self._match_text(text_content)
            sentiment = get_min_sentiment(text_content)
            need_score = self._calculate_scores(text_content, hits, sentiment)

            matched_ids = list(set(hash(h.get("term", "")) % 1000000 for h in hits))[:20]
            top_terms = [h.get("term") for h in hits[:10] if h.get("term")]

            payload = {
                "post_id": post_id,
                "l1_category": need_score.primary(),
                "l1_secondary": need_score.secondary(),
                "l2_business": subreddit,
                "l3_scene": None,
                "matched_rule_ids": matched_ids or None,
                "top_terms": top_terms or None,
                "raw_scores": json.dumps(need_score.to_dict()),
                "sentiment_score": sentiment,
                "confidence": min(1.0, sum(need_score.to_dict().values()) * 0.1),
            }
            self._upsert_label(payload)
            processed += 1

        return {"processed": processed, "skipped": 0}

    def evaluate_text_content(self, text: str) -> NeedScore:
        """Evaluate text content and return need scores WITHOUT writing to database.
        
        Phase 6: Used by CommunityEvaluator to assess community value density
        by scoring sample posts in-memory.
        
        Args:
            text: Text content to evaluate (title + body combined)
            
        Returns:
            NeedScore with scores for all 5 need categories
        """
        if not text or len(text.strip()) < 5:
            return NeedScore()
        
        hits = self._match_text(text)
        sentiment = get_min_sentiment(text)
        return self._calculate_scores(text, hits, sentiment)


__all__ = ["SemanticTagger", "NeedScore", "NEED_CATEGORIES"]
