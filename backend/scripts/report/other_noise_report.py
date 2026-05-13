#!/usr/bin/env python3
"""
Generate OTHER ratio & noise rate report.
Outputs reports/local-acceptance/other-ratio.json
"""
import asyncio
import json
from pathlib import Path
from app.db.session import SessionFactory
from sqlalchemy import text


async def main() -> None:
    out_path = Path("reports/local-acceptance/other-ratio.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result: dict = {}
    async with SessionFactory() as session:
        # OTHER ratio from content_labels
        sql_other = text(
            """
            SELECT content_type,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE COALESCE(aspect, category) = 'OTHER') AS other_cnt
            FROM content_labels
            GROUP BY content_type
            """
        )
        rows = await session.execute(sql_other)
        result["other_ratio"] = []
        for row in rows.fetchall():
            total = max(1, int(row.total or 0))
            other_cnt = int(row.other_cnt or 0)
            result["other_ratio"].append(
                {
                    "content_type": row.content_type,
                    "total": total,
                    "other": other_cnt,
                    "other_ratio": round(other_cnt / total, 4),
                }
            )

        # Noise rate per subreddit (posts + comments, last 30d)
        sql_noise = text(
            """
            WITH posts AS (
                SELECT p.subreddit, COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE nl.id IS NOT NULL) AS noise_cnt
                FROM posts_raw p
                LEFT JOIN noise_labels nl
                  ON nl.content_type = 'post' AND nl.content_id = p.id
                WHERE p.created_at >= NOW() - INTERVAL '30 days'
                  AND p.is_current = true
                GROUP BY p.subreddit
            ), comments AS (
                SELECT c.subreddit, COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE nl.id IS NOT NULL) AS noise_cnt
                FROM comments c
                LEFT JOIN noise_labels nl
                  ON nl.content_type = 'comment' AND nl.content_id = c.id
                WHERE c.created_utc >= NOW() - INTERVAL '30 days'
                GROUP BY c.subreddit
            )
            SELECT lower(coalesce(p.subreddit, c.subreddit)) AS subreddit,
                   COALESCE(p.total,0) + COALESCE(c.total,0) AS total,
                   COALESCE(p.noise_cnt,0) + COALESCE(c.noise_cnt,0) AS noise_cnt
            FROM posts p
            FULL OUTER JOIN comments c ON p.subreddit = c.subreddit
            WHERE COALESCE(p.total,0) + COALESCE(c.total,0) > 0
            ORDER BY noise_cnt DESC
            LIMIT 50;
            """
        )
        rows = await session.execute(sql_noise)
        result["noise_by_subreddit"] = []
        for row in rows.fetchall():
            total = max(1, int(row.total or 0))
            noise_cnt = int(row.noise_cnt or 0)
            result["noise_by_subreddit"].append(
                {
                    "subreddit": row.subreddit,
                    "total": total,
                    "noise": noise_cnt,
                    "noise_ratio": round(noise_cnt / total, 4),
                }
            )

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ OTHER/noise report written: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
