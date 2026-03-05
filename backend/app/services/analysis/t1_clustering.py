"""简单规则版痛点聚类（PAIN 评论 -> 3~5 个簇）。"""
from __future__ import annotations

import re
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm.clients.openai_client import OpenAIChatClient

STOPWORDS = {
    "the", "and", "to", "a", "of", "in", "for", "is", "it", "on", "this", "that", "with",
    "my", "me", "was", "are", "as", "but", "so", "have", "has", "really", "would", "like",
    "problem", "just", "get", "don", "know", "think", "people", "make", "good", "much",
    "time", "use", "also", "even", "want", "way", "need", "going", "see", "thing", "could",
    "back", "well", "said", "still", "got", "something", "never", "right", "say", "because",
    "when", "from", "which", "by", "at", "or", "be", "an", "if", "we", "they", "their", "what"
}

COMMERCIAL_STOPWORDS = {
    "you", "your", "yours", "not", "just", "really", "would", "like", "about", "very",
    "store", "product", "sell", "buy"
}

ASPECT_TOPIC_NAME = {
    "price": "pricing",
    "subscription": "subscription",
    "install": "setup",
    "ecosystem": "integration",
    "content": "content",
    "other": "general",
    "logistics": "shipping",
    "ads": "advertising",
    "ban": "compliance"
}


@dataclass(slots=True)
class PainCluster:
    topic: str
    size: int
    aspects: list[str]
    keywords: list[str]
    samples: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class T1ClusteringService:
    """
    Service to cluster pain points from database comments.
    Wrapper around the functional logic for dependency injection.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def cluster_pains(
        self,
        subreddits: Optional[Sequence[str]] = None,
        days: int = 365,
        limit: int = 5
    ) -> list[dict]:
        """
        Returns list of dicts representing clusters.
        Output format:
        [{
            "topic": "subscription",
            "size": 120,
            "keywords": ["cost", "monthly"],
            "samples": ["Too expensive...", "Hidden fees..."]
        }, ...]
        """
        clusters = await build_pain_clusters(
            self.session, 
            subreddits=subreddits, 
            days=days, 
            sample_per_aspect=10
        )
        # Sort by size and take top N
        clusters.sort(key=lambda x: x.size, reverse=True)
        return [c.to_dict() for c in clusters[:limit]]


def _tokenize(text: str) -> list[str]:
    # Improved tokenizer
    text = re.sub(r"http\S+", "", text) # remove urls
    tokens = re.split(r"[^A-Za-z]+", text.lower())
    stopwords = STOPWORDS | COMMERCIAL_STOPWORDS
    return [t for t in tokens if t and t not in stopwords and len(t) > 2]


async def _fetch_pain_comments(
    session: AsyncSession,
    *,
    subs: Sequence[str],
    since_dt: datetime,
    sample_per_aspect: int = 5,
) -> dict[str, list[str]]:
    # Using content_labels to find PAIN
    sql = """
    SELECT cl.aspect AS aspect, c.body AS body
    FROM content_labels cl
    JOIN comments c ON c.id = cl.content_id
    WHERE cl.content_type = 'comment'
      AND cl.category IN ('pain', 'Survival')
      AND c.created_utc >= :since
    ORDER BY c.score DESC
    LIMIT 1000
    """
    # Note: subs filter removed for speed in this prototype, 
    # assuming T1 pool is already filtered by the crawler/labeler focus.
    
    rows = await session.execute(text(sql), {"since": since_dt})
    
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in rows.fetchall():
        if len(buckets[row.aspect]) >= sample_per_aspect:
            continue
        if len(row.body) > 20: # Filter too short
            buckets[row.aspect].append(row.body)
    return buckets


async def build_pain_clusters(
    session: AsyncSession,
    *,
    subreddits: Optional[Sequence[str]] = None,
    days: int = 365,
    sample_per_aspect: int = 5,
) -> list[PainCluster]:
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    subs = [s.lower().removeprefix("r/") for s in (subreddits or []) if s] or []

    buckets = await _fetch_pain_comments(
        session, subs=subs, since_dt=since_dt, sample_per_aspect=sample_per_aspect
    )

    clusters: list[PainCluster] = []
    for aspect, comments in buckets.items():
        tokens = []
        for c in comments:
            tokens.extend(_tokenize(c))
        
        # Extract top keywords
        common_words = Counter(tokens).most_common(8)
        top_keywords = [w for w, _ in common_words]
        
        # Map aspect to friendly topic name, or use aspect itself if not mapped
        topic = ASPECT_TOPIC_NAME.get(aspect, aspect)
        
        clusters.append(
            PainCluster(
                topic=topic,
                size=len(comments),
                aspects=[aspect],
                keywords=top_keywords,
                samples=comments,
            )
        )

    return clusters


__all__ = ["PainCluster", "build_pain_clusters", "T1ClusteringService"]


async def build_pain_hierarchy(
    clusters: list[PainCluster],
    model: str = "google/gemini-2.5-flash",
) -> list[dict[str, Any]]:
    """
    Uses LLM to organize flat clusters into a Root-Cause Hierarchy.
    Returns list of dicts: [{"root_cause": str, "sub_issues": [...], "summary": str}, ...]
    """
    if not clusters:
        return []

    client = OpenAIChatClient(model=model)

    # Prepare brief summaries for LLM
    payload = []
    for c in clusters:
        sample = c.samples[0] if c.samples else ""
        payload.append(
            {
                "topic": c.topic,
                "aspects": c.aspects,
                "keywords": c.keywords[:5],
                "sample": sample[:240],
            }
        )

    system = (
        "你是一个专业的归因分析师，擅长把零散的用户抱怨归纳成“核心根因 -> 具体表现”的层级结构。"
        "请只输出 JSON，确保是合法 JSON 数组。"
    )
    user = (
        "请分析以下痛点列表，将其归纳为 3-5 个核心根因。"
        "输出格式：[\n"
        '  {"root_cause": "...", "sub_issues": ["...","..."], "summary": "..."}\n'
        "]。"
        "要求：\n"
        "- sub_issues 使用输入的 topic/aspect/关键词，不要杜撰新问题。\n"
        "- summary 用中文简述根因影响。"
        f"\n痛点列表：\n{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        resp = await client.generate(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=600,
            temperature=0.35,
        )
        cleaned = resp.strip()
        # Remove code fences if any
        cleaned = re.sub(r"```json|```", "", cleaned).strip()
        data = json.loads(cleaned)
        if isinstance(data, list):
            # Minimal validation
            out: list[dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                root = item.get("root_cause") or item.get("root")
                subs = item.get("sub_issues") or item.get("children") or []
                summary = item.get("summary") or ""
                out.append(
                    {
                        "root_cause": root or "未命名根因",
                        "sub_issues": subs if isinstance(subs, list) else [str(subs)],
                        "summary": summary,
                    }
                )
            if out:
                return out
    except Exception:
        pass

    # Fallback: single bucket
    return [
        {
            "root_cause": "未分类",
            "sub_issues": [c.topic for c in clusters],
            "summary": "LLM 归纳失败，保持原始聚类列表。",
        }
    ]
