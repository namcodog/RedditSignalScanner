#!/usr/bin/env python3
"""
HDBSCAN 聚类挖掘痛点簇，用于发现未知的细分 Aspect。

用法示例：
  PYTHONPATH=$(pwd)/backend python -m backend.scripts.cluster_mining --aspect subscription --limit 100000 --min-cluster-size 20 --top-keywords 8

输出：
  reports/local-acceptance/cluster_mining_<aspect>.json
包含 cluster_id、keywords、sample_count、sample_texts。
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sqlalchemy import text
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

from app.db.session import SessionFactory


async def fetch_texts_embeddings(
    aspect: str,
    limit: int,
) -> Tuple[List[str], np.ndarray]:
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT c.id,
                       COALESCE(c.title, '') || ' ' || COALESCE(c.body, '') AS text,
                       pe.embedding AS emb
                FROM content_labels cl
                JOIN posts_raw c ON c.id = cl.content_id
                JOIN post_embeddings pe ON pe.post_id = c.id
                JOIN community_pool cp ON lower(cp.name) = lower(c.subreddit)
                WHERE cl.category = 'pain'
                  AND cl.aspect = :aspect
                  AND cp.is_active = true
                  AND cp.deleted_at IS NULL
                ORDER BY cl.id
                LIMIT :lim
                """
            ),
            {"aspect": aspect, "lim": limit},
        )
        texts: List[str] = []
        embs: List[np.ndarray] = []
        for row in rows.mappings():
            txt = (row.get("text") or "").strip()
            emb = row.get("emb")
            if not txt or not emb:
                continue
            try:
                if isinstance(emb, str):
                    emb_parsed = np.array(json.loads(emb), dtype=np.float64)
                else:
                    emb_parsed = np.array(list(emb), dtype=np.float64)
            except Exception:
                continue
            texts.append(txt)
            embs.append(emb_parsed)
        if not embs:
            return [], np.empty((0, 0))
        return texts, np.vstack(embs)


def cluster_texts(texts: List[str], embs: np.ndarray, min_cluster_size: int) -> List[int]:
    if embs.shape[0] == 0:
        return []
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embs)
    return labels.tolist()


def extract_keywords_for_cluster(cluster_texts: List[str], top_k: int) -> List[str]:
    if not cluster_texts:
        return []
    vectorizer = TfidfVectorizer(
        max_features=max(50, top_k * 4),
        stop_words="english",
        ngram_range=(1, 3),
    )
    tfidf = vectorizer.fit_transform(cluster_texts)
    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf.sum(axis=0).A1
    top_idx = scores.argsort()[-top_k:][::-1]
    return [feature_names[i] for i in top_idx if i < len(feature_names)]


async def mine(aspect: str, limit: int, min_cluster_size: int, top_keywords: int) -> list[dict]:
    texts, embs = await fetch_texts_embeddings(aspect, limit)
    if embs.shape[0] == 0:
        print("⚠️ No embeddings found for aspect:", aspect)
        return []
    labels = cluster_texts(texts, embs, min_cluster_size=min_cluster_size)
    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue  # 噪声
        clusters.setdefault(label, []).append(idx)

    out: list[dict] = []
    for cid, idxs in clusters.items():
        cluster_samples = [texts[i] for i in idxs]
        keywords = extract_keywords_for_cluster(cluster_samples, top_keywords)
        out.append(
            {
                "cluster_id": int(cid),
                "sample_count": len(idxs),
                "keywords": keywords,
                "sample_texts": cluster_samples[:3],
            }
        )
    out.sort(key=lambda x: -x["sample_count"])
    return out


async def main() -> None:
    parser = argparse.ArgumentParser(description="HDBSCAN-based cluster mining for aspects.")
    parser.add_argument("--aspect", default="subscription", help="Target aspect (e.g., subscription, other)")
    parser.add_argument("--limit", type=int, default=100000, help="Max rows to load")
    parser.add_argument("--min-cluster-size", type=int, default=20, help="HDBSCAN min_cluster_size")
    parser.add_argument("--top-keywords", type=int, default=8, help="Top TF-IDF keywords per cluster")
    args = parser.parse_args()

    clusters = await mine(
        aspect=args.aspect,
        limit=args.limit,
        min_cluster_size=args.min_cluster_size,
        top_keywords=args.top_keywords,
    )

    out_path = Path("reports/local-acceptance") / f"cluster_mining_{args.aspect}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(clusters, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Clusters exported: {out_path} (count={len(clusters)})")


if __name__ == "__main__":
    asyncio.run(main())
