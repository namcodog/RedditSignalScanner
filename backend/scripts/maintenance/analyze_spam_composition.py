"""
垃圾成分分析脚本 (Spam Composition Analyzer)

功能：
- 分析 spam_category 分布
- 统计各类垃圾的数量和占比
- 输出高频垃圾关键词，用于优化黑名单

用法：
    python backend/scripts/maintenance/analyze_spam_composition.py --days 30

输出示例：
    📊 垃圾成分分析 (最近 30 天)
    ----------------------------------------
    Spam_Bot:        1,234 (40.5%)
    Spam_Ad:         892   (29.2%)
    Spam_Crypto:     521   (17.1%)
    Spam_LowQuality: 403   (13.2%)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze spam composition.")
    parser.add_argument("--days", type=int, default=30, help="Lookback days.")
    parser.add_argument("--top-phrases", type=int, default=20, help="Top spam phrases to show.")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url.replace("asyncpg", "psycopg"), future=True)

    # 1. 分类分布
    category_sql = text("""
        SELECT 
            COALESCE(spam_category, 'Clean') AS category,
            COUNT(*) AS cnt
        FROM posts_raw
        WHERE created_at >= NOW() - (interval '1 day' * :days)
          AND is_current = true
        GROUP BY category
        ORDER BY cnt DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(category_sql, {"days": args.days}).mappings().all()

    total = sum(r["cnt"] for r in rows)
    print(f"\n📊 垃圾成分分析 (最近 {args.days} 天)")
    print("-" * 40)
    for row in rows:
        cat = row["category"]
        cnt = row["cnt"]
        pct = (cnt / total * 100) if total > 0 else 0
        print(f"  {cat:<20} {cnt:>8,} ({pct:.1f}%)")
    print("-" * 40)
    print(f"  {'TOTAL':<20} {total:>8,}")

    # 2. 高频垃圾短语提取 (仅从有 spam_category 的帖子中提取)
    phrase_sql = text("""
        SELECT title, body
        FROM posts_raw
        WHERE created_at >= NOW() - (interval '1 day' * :days)
          AND spam_category IS NOT NULL
        LIMIT 5000
    """)

    with engine.connect() as conn:
        spam_posts = conn.execute(phrase_sql, {"days": args.days}).mappings().all()

    if spam_posts:
        import re
        stop_words = {
            "the", "a", "an", "to", "for", "and", "with", "that", "this", "in", "on", "of",
            "is", "it", "my", "me", "we", "you", "your", "are", "be", "was", "were", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
            "i", "am", "just", "so", "but", "or", "if", "how", "what", "when", "where", "who",
            "all", "can", "get", "got", "like", "know", "want", "need", "make", "made",
        }

        bigrams: Counter[str] = Counter()
        for row in spam_posts:
            txt = re.sub(r"[^a-z0-9\s]", "", f"{row['title'] or ''} {row['body'] or ''}".lower())
            tokens = [t for t in txt.split() if len(t) > 2 and t not in stop_words]
            for i in range(len(tokens) - 1):
                bigrams[f"{tokens[i]} {tokens[i+1]}"] += 1

        print(f"\n🔍 高频垃圾短语 (Top {args.top_phrases})")
        print("-" * 40)
        for phrase, count in bigrams.most_common(args.top_phrases):
            print(f"  \"{phrase}\": {count}")

    print("\n✅ 分析完成。可根据以上数据优化 community_blacklist.yaml。\n")


if __name__ == "__main__":
    main()
