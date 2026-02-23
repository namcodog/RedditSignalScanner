"""
作者黑名单建议生成脚本

逻辑：
- 满足配置 author_auto_blacklist_rules 的作者输出为建议黑名单
- 规则：min_posts、avg_score_below、spam_hit_rate_above
- 输出 CSV 到 stdout，格式：username,reason,posts,avg_score,spam_hits,total_hits

使用示例：
    python backend/scripts/suggest_author_blacklist.py --limit 5000
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.config import get_settings  # noqa: E402
from app.services.blacklist_loader import BlacklistConfig  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest author blacklist entries.")
    parser.add_argument("--limit", type=int, default=10000, help="Max authors to scan.")
    args = parser.parse_args()

    cfg = BlacklistConfig()
    rules = cfg.author_auto_rules or {}
    min_posts = int(rules.get("min_posts", 3))
    avg_score_below = float(rules.get("avg_score_below", 1))
    spam_hit_rate_above = float(rules.get("spam_hit_rate_above", 0.5))

    settings = get_settings()
    engine = create_engine(settings.database_url.replace("asyncpg", "psycopg"), future=True)

    query = text(
        """
        WITH author_stats AS (
            SELECT
                author_name,
                COUNT(*) AS posts,
                AVG(score) AS avg_score,
                AVG(CASE WHEN is_spam = TRUE THEN 1.0 ELSE 0.0 END) AS spam_rate
            FROM posts_raw
            WHERE author_name IS NOT NULL AND author_name <> ''
            GROUP BY author_name
            ORDER BY posts DESC
            LIMIT :limit
        )
        SELECT author_name, posts, avg_score, spam_rate
        FROM author_stats
        WHERE posts >= :min_posts
          AND COALESCE(avg_score, 0) < :avg_score_below
          AND COALESCE(spam_rate, 0) > :spam_hit_rate_above
        """
    )

    rows = []
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "limit": args.limit,
                "min_posts": min_posts,
                "avg_score_below": avg_score_below,
                "spam_hit_rate_above": spam_hit_rate_above,
            },
        ).mappings().all()

    writer = csv.writer(sys.stdout)
    writer.writerow(["username", "reason", "posts", "avg_score", "spam_rate"])
    for row in rows:
        writer.writerow(
            [
                row["author_name"],
                f"posts>={min_posts}, avg_score<{avg_score_below}, spam_rate>{spam_hit_rate_above}",
                row["posts"],
                f"{row['avg_score']:.2f}" if row["avg_score"] is not None else "",
                f"{row['spam_rate']:.2f}" if row["spam_rate"] is not None else "",
            ]
        )


if __name__ == "__main__":
    main()
