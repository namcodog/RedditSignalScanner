"""
V3.0 语义挖掘主脚本（Phase 3.1 融合方案）

Phase A: Smart Loader
  - Filter 1: score > 2
  - Filter 2: 向量距离（与垃圾中心 > 0.3）
  - Filter 3: 非黑名单社区

Phase B: Deep Cleaner
  - 清洗 URL/Email/Markdown
  - 长句 DF > 0.3 删除
  - 短句 Exact Match 去重（text_norm_hash 逻辑）

Phase C: Layer Router
  - 按 subreddit 分配 L1/L2/L3

Phase D: NLP Extractor
  - 提取 Noun Phrases
  - 计算 Negative Sentiment 共现

Phase E: Persist
  - 写入 semantic_rules（meta 含 layer）
"""

from __future__ import annotations

import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

import numpy as np
import yaml
from sqlalchemy import create_engine, text

# 确保可以找到 app 模块
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.config import get_settings
from app.services.analysis.text_cleaner import (
    clean_template_sentences,
    clean_text,
    split_sentences,
)
from app.services.semantic.layer_router import DEFAULT_LAYER_MAP, LayerRouter

SPAM_THRESHOLD = 0.3
SCORE_THRESHOLD = 2
SAMPLE_LIMIT = 5000
CONCEPT_CODE = "semantic_layers_v3"
CONCEPT_NAME = "Semantic Layered Rules V3"
SPAM_CENTROIDS_PATH = Path(__file__).resolve().parents[2] / "data" / "spam_centroids.pkl"
BLACKLIST_PATH = Path(__file__).resolve().parents[2] / "config" / "community_blacklist.yaml"

# 精简负向情绪词表（共现判断）
NEGATIVE_TERMS = {
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
    "error",
    "fail",
    "crash",
    "scam",
    "spam",
}

# 停用词表：这些词开头/结尾的短语直接丢弃
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "this", "that", "these", "those", "it", "its", "i", "you", "he", "she",
    "we", "they", "my", "your", "his", "her", "our", "their", "me", "him",
    "us", "them", "who", "what", "which", "when", "where", "how", "why",
    "all", "any", "some", "no", "not", "only", "just", "also", "very",
    "so", "too", "up", "down", "out", "off", "over", "under", "again",
    "then", "than", "now", "here", "there", "if", "because", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "same", "other", "such", "even", "more", "most", "one",
    "two", "first", "last", "own", "new", "old", "right", "back", "get",
    "got", "like", "know", "think", "want", "need", "see", "come", "go",
    "make", "take", "give", "tell", "say", "said", "told", "and", "aita",
}


def _get_engine():
    settings = get_settings()
    url = settings.database_url.replace("asyncpg", "psycopg")
    return create_engine(url, future=True)


def _load_spam_centroids(path: Path = SPAM_CENTROIDS_PATH) -> np.ndarray | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            arr = pickle.load(f)
            return np.array(arr)
    except Exception:
        return None


def _load_blacklist(path: Path = BLACKLIST_PATH) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()
    blocked: set[str] = set()
    for entry in data.get("blacklisted_communities", []) or []:
        name = entry.get("name") if isinstance(entry, Mapping) else entry
        if name:
            blocked.add(LayerRouter.normalize_subreddit(str(name)))
    for name in data.get("blacklist", []) or []:
        if name:
            blocked.add(LayerRouter.normalize_subreddit(str(name)))
    return blocked


def _parse_embedding(raw) -> np.ndarray | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, np.ndarray)):
        try:
            return np.array(raw, dtype=float)
        except Exception:
            return None
    try:
        txt = str(raw).strip()
        txt = txt.strip("[]{}()")
        parts = [p for p in txt.split(",") if p.strip()]
        return np.array([float(p) for p in parts], dtype=float)
    except Exception:
        return None


def _distance_to_centroids(vec: np.ndarray, centroids: np.ndarray | None) -> float:
    if centroids is None or centroids.size == 0:
        return 1.0
    try:
        # 维度不一致时跳过距离过滤
        if centroids.shape[1] != vec.shape[0]:
            return 1.0
        distances = [np.linalg.norm(vec - center) for center in centroids]
        return min(distances) if distances else 1.0
    except Exception:
        return 1.0


def _normalize_for_df(sentence: str) -> str:
    lowered = sentence.lower().strip()
    alpha_numeric = re.sub(r"[^a-z0-9\s]", " ", lowered)
    squashed = re.sub(r"\s+", " ", alpha_numeric)
    return squashed.strip()


def _build_df_lookup(texts: Iterable[str]):
    normalized_counts: Counter[str] = Counter()
    total_docs = 0

    for text in texts:
        total_docs += 1
        seen_in_doc: set[str] = set()
        for sent in split_sentences(text):
            norm = _normalize_for_df(sent)
            if norm:
                seen_in_doc.add(norm)
        for norm in seen_in_doc:
            normalized_counts[norm] += 1

    def lookup(sentence: str) -> float:
        if total_docs == 0:
            return 0.0
        key = _normalize_for_df(sentence)
        return normalized_counts.get(key, 0) / float(total_docs)

    return lookup


def _extract_noun_phrases(text: str, limit: int = 5) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)
    phrases: Counter[str] = Counter()
    for i in range(len(tokens) - 1):
        first, second = tokens[i], tokens[i + 1]
        first_lower, second_lower = first.lower(), second.lower()
        # 过滤：词长 < 3 或首尾是停用词
        if len(first) < 3 or len(second) < 3:
            continue
        if first_lower in STOPWORDS or second_lower in STOPWORDS:
            continue
        phrases[f"{first_lower} {second_lower}"] += 1
    # 单词短语也需过滤停用词
    if not phrases:
        for token in tokens:
            token_lower = token.lower()
            if len(token) >= 4 and token_lower not in STOPWORDS:
                phrases[token_lower] += 1
    return [phrase for phrase, _ in phrases.most_common(limit)]


def _detect_negative_hits(text: str) -> List[str]:
    lowered = text.lower()
    hits = [term for term in NEGATIVE_TERMS if term in lowered]
    return sorted(set(hits))


def _fetch_candidates(conn, centroids: np.ndarray | None, blacklist: set[str]) -> List[Dict]:
    rows = conn.execute(
        text(
            """
            SELECT pr.id, pr.title, pr.body, pr.subreddit, pr.score, pe.embedding
            FROM posts_raw pr
            JOIN post_embeddings pe ON pe.post_id = pr.id
            WHERE pr.is_current = true
              AND pr.score > :score_threshold
            ORDER BY pr.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": SAMPLE_LIMIT, "score_threshold": SCORE_THRESHOLD},
    ).mappings().all()

    candidates: List[Dict] = []
    for row in rows:
        sub = LayerRouter.normalize_subreddit(str(row.get("subreddit") or ""))
        if sub in blacklist:
            continue
        vec = _parse_embedding(row.get("embedding"))
        if vec is None:
            continue
        if _distance_to_centroids(vec, centroids) < SPAM_THRESHOLD:
            continue
        text_blob = f"{row.get('title') or ''}\n{row.get('body') or ''}".strip()
        if not text_blob:
            continue
        candidates.append(
            {
                "post_id": row.get("id"),
                "subreddit": sub,
                "raw_text": text_blob,
            }
        )
    return candidates


def _prepare_cleaned_texts(candidates: List[Dict]) -> List[Dict]:
    texts = [clean_text(item["raw_text"]) for item in candidates]
    df_lookup = _build_df_lookup(texts)
    seen_hashes: set[str] = set()
    cleaned_candidates: List[Dict] = []

    for item, cleaned in zip(candidates, texts):
        templated = clean_template_sentences(cleaned, df_lookup=df_lookup, seen_hashes=seen_hashes)
        if not templated:
            continue
        cloned = dict(item)
        cloned["cleaned_text"] = templated
        cleaned_candidates.append(cloned)
    return cleaned_candidates


def _collect_rule_acc(items: List[Dict], router: LayerRouter):
    acc: Dict[Tuple[str, str], Dict] = {}
    for item in items:
        layer, sub = router.route(item["subreddit"])
        text_blob = item["cleaned_text"]
        phrases = _extract_noun_phrases(text_blob)
        if not phrases:
            continue
        neg_hits = _detect_negative_hits(text_blob)
        for phrase in phrases:
            key = (phrase, layer)
            bucket = acc.setdefault(
                key,
                {"freq": 0, "subreddits": Counter(), "neg_hits": Counter(), "examples": []},
            )
            bucket["freq"] += 1
            bucket["subreddits"][sub] += 1
            for hit in neg_hits:
                bucket["neg_hits"][hit] += 1
            if len(bucket["examples"]) < 3:
                bucket["examples"].append(text_blob[:200])
    return acc


def _to_rule_rows(acc: Dict[Tuple[str, str], Dict]) -> List[Dict]:
    rows: List[Dict] = []
    today = date.today().isoformat()
    for (phrase, layer), payload in acc.items():
        freq = payload.get("freq", 0)
        subs: Counter[str] = payload.get("subreddits", Counter())
        top_sub = subs.most_common(1)[0][0] if subs else "r/unknown"
        neg_hits = [term for term, _ in payload.get("neg_hits", Counter()).most_common(5)]
        confidence = min(0.95, 0.5 + 0.05 * freq + 0.05 * len(neg_hits))
        weight = min(1.0, 0.4 + 0.05 * freq)
        meta = {
            "layer": layer,
            "source_sub": top_sub,
            "confidence": round(confidence, 3),
            "extracted_at": today,
            "negative_hits": neg_hits,
        }
        rows.append({"term": phrase, "weight": weight, "meta": json.dumps(meta)})
    return rows


def _ensure_concept(conn) -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO semantic_concepts(code, name, description, domain, is_active)
            VALUES (:code, :name, :desc, 'general', true)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                is_active = true,
                updated_at = NOW()
            RETURNING id
            """
        ),
        {"code": CONCEPT_CODE, "name": CONCEPT_NAME, "desc": "Semantic layer mining v3.0"},
    ).scalar_one()
    return int(row)


def _persist_rules(conn, concept_id: int, rows: List[Dict]) -> int:
    if not rows:
        return 0
    stmt = text(
        """
        INSERT INTO semantic_rules (concept_id, term, rule_type, weight, meta)
        VALUES (:cid, :term, 'keyword', :weight, CAST(:meta AS JSONB))
        ON CONFLICT (concept_id, term, rule_type)
        DO UPDATE SET
            weight = EXCLUDED.weight,
            meta = EXCLUDED.meta,
            updated_at = NOW(),
            is_active = true
        """
    )
    params = [{"cid": concept_id, "term": row["term"], "weight": row["weight"], "meta": row["meta"]} for row in rows]
    conn.execute(stmt, params)
    return len(rows)


def main() -> None:
    centroids = _load_spam_centroids()
    if centroids is None:
        print("⚠️ 未找到 spam_centroids.pkl，跳过向量距离过滤。")
    blacklist = _load_blacklist()
    router = LayerRouter(mapping=DEFAULT_LAYER_MAP)

    engine = _get_engine()
    with engine.connect() as conn:
        candidates = _fetch_candidates(conn, centroids, blacklist)

    if not candidates:
        print("⚠️ 未找到符合条件的帖子，终止。")
        return

    cleaned = _prepare_cleaned_texts(candidates)
    if not cleaned:
        print("⚠️ 清洗后无有效文本，终止。")
        return

    acc = _collect_rule_acc(cleaned, router)
    rows = _to_rule_rows(acc)

    if not rows:
        print("⚠️ 未生成任何规则，终止。")
        return

    with engine.begin() as conn:
        cid = _ensure_concept(conn)
        inserted = _persist_rules(conn, cid, rows)

    print(f"🎯 已写入/更新 {inserted} 条规则到 semantic_rules（concept={CONCEPT_CODE}）")


if __name__ == "__main__":
    main()
