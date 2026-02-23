"""
构建垃圾多中心向量（Multi-Centroid Spam Filter）

流程：
1) 从 semantic_rules 读取全局过滤关键词（concept=global_filter_keywords）
2) 在 posts_raw 中匹配包含这些关键词的帖子（LIMIT 2000）
3) 提取对应 post_embeddings
4) KMeans(K=3) 聚类，生成 3 个垃圾中心
5) 保存到 backend/data/spam_centroids.pkl
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy import create_engine, text

# 确保可以找到 app 模块
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.config import get_settings

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "spam_centroids.pkl"
FILTER_CONCEPT = "global_filter_keywords"
SAMPLE_LIMIT = 2000


def _get_engine():
    settings = get_settings()
    url = settings.database_url.replace("asyncpg", "psycopg")
    return create_engine(url, future=True)


def _load_filter_keywords(conn) -> List[str]:
    rows = conn.execute(
        text(
            """
            SELECT r.term
            FROM semantic_rules r
            JOIN semantic_concepts c ON c.id = r.concept_id
            WHERE c.code = :code AND r.is_active = true
            ORDER BY r.id ASC
            """
        ),
        {"code": FILTER_CONCEPT},
    ).scalars()
    return [str(term).strip().lower() for term in rows if term]


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


def _fetch_spam_embeddings(conn, keywords: List[str]) -> List[np.ndarray]:
    if not keywords:
        return []

    clauses = []
    params: Dict[str, str] = {}
    for idx, kw in enumerate(keywords):
        param = f"kw{idx}"
        params[param] = f"%{kw}%"
        clauses.append(f"(pr.title ILIKE :{param} OR pr.body ILIKE :{param})")
    where_clause = " OR ".join(clauses)

    query = text(
        f"""
        SELECT pr.id, pe.embedding
        FROM posts_raw pr
        JOIN post_embeddings pe ON pe.post_id = pr.id
        WHERE pr.is_current = true
          AND ({where_clause})
        LIMIT :limit
        """
    )
    params["limit"] = SAMPLE_LIMIT

    rows = conn.execute(query, params).mappings().all()
    vectors: List[np.ndarray] = []
    for row in rows:
        vec = _parse_embedding(row.get("embedding"))
        if vec is not None:
            vectors.append(vec)
    return vectors


def _run_kmeans(vectors: List[np.ndarray]) -> np.ndarray:
    mat = np.vstack(vectors)
    model = KMeans(n_clusters=3, n_init=10, random_state=42)
    model.fit(mat)
    return model.cluster_centers_


def main() -> None:
    engine = _get_engine()
    with engine.connect() as conn:
        keywords = _load_filter_keywords(conn)
        if not keywords:
            print("❌ 未找到垃圾过滤关键词，终止。")
            return
        print(f"✅ 载入垃圾关键词 {len(keywords)} 条")

        vectors = _fetch_spam_embeddings(conn, keywords)

    if len(vectors) < 3:
        print(f"⚠️ 样本不足（{len(vectors)} 条），无法聚类。")
        return

    centers = _run_kmeans(vectors)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("wb") as f:
        pickle.dump(centers, f)
    print(f"🎯 已生成 3 个垃圾中心 → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
