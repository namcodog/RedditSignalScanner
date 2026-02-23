"""
标记语义重复帖子（策略B：异步标记，不阻塞入库）

逻辑：
- 扫描最近 N 条 posts_raw（默认 1000）
- 对每条，查询 post_embeddings 余弦相似度 > 0.95 且时间差 < 24h 的记录
- 命中后：posts_raw.is_duplicate = TRUE, duplicate_of_id = 原帖 ID

注意：
- 依赖 post_embeddings 向量索引（建议 HNSW/IVFFlat），否则性能较差
- 仅更新 posts_raw，不触碰社区/社区抓取表

用法：
    python backend/scripts/mark_duplicates.py --limit 1000 --threshold 0.95
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.config import get_settings  # noqa: E402


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def parse_embedding(raw) -> np.ndarray | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, np.ndarray)):
        return np.array(raw, dtype=float)
    try:
        txt = str(raw).strip("[](){}")
        vals = [float(x) for x in txt.split(",") if x.strip()]
        return np.array(vals, dtype=float)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark duplicate posts via vector similarity.")
    parser.add_argument("--limit", type=int, default=1000, help="Number of recent posts to scan.")
    parser.add_argument("--threshold", type=float, default=0.95, help="Cosine similarity threshold.")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url.replace("asyncpg", "psycopg"), future=True)

    recent_query = text(
        """
        SELECT id, created_at
        FROM posts_raw
        WHERE is_current = true
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )

    embed_query = text(
        """
        SELECT post_id, embedding, created_at
        FROM post_embeddings
        WHERE post_id = ANY(:ids)
        """
    )

    update_stmt = text(
        """
        UPDATE posts_raw
        SET is_duplicate = TRUE, duplicate_of_id = :dup_id
        WHERE id = :target_id
        """
    )

    with engine.connect() as conn:
        posts = conn.execute(recent_query, {"limit": args.limit}).mappings().all()
        if not posts:
            print("⚠️ No posts to scan.")
            return
        ids = [int(p["id"]) for p in posts]
        post_meta = {int(p["id"]): p["created_at"] for p in posts}

        embed_rows = conn.execute(embed_query, {"ids": ids}).mappings().all()
        vectors = {}
        for row in embed_rows:
            vec = parse_embedding(row.get("embedding"))
            if vec is not None:
                vectors[int(row["post_id"])] = (vec, row.get("created_at"))

    marked = 0
    checked = 0
    with engine.begin() as conn:
        id_list = list(vectors.keys())
        for i, pid in enumerate(id_list):
            vec_i, ts_i = vectors[pid]
            for j in range(i):
                other_id = id_list[j]
                vec_j, ts_j = vectors[other_id]
                # 时间窗 24h
                if ts_i and ts_j:
                    dt = abs(ts_i - ts_j)
                    if dt > timedelta(hours=24):
                        continue
                sim = cosine_similarity(vec_i, vec_j)
                checked += 1
                if sim >= args.threshold:
                    # 标记较新的为重复
                    dup_id = other_id if (ts_j and ts_i and ts_j <= ts_i) else pid
                    target_id = pid if dup_id == other_id else other_id
                    conn.execute(update_stmt, {"dup_id": dup_id, "target_id": target_id})
                    marked += 1
                    break

    print(f"✅ duplicate scan completed. checked={checked}, marked={marked}")


if __name__ == "__main__":
    main()
