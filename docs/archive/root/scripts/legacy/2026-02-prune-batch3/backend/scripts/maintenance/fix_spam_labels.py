"""
Spam 记录修复脚本

功能：
1. 找出 l1_category = 'Spam' 的记录
2. 重新计算需求分类（使用关键词匹配）
3. 把 l1_category 更新为正确的分类，把 spam 移到 tags 里

安全措施：
- 只 UPDATE，不 DELETE
- 分批处理
- 详细日志

用法：
    python backend/scripts/maintenance/fix_spam_labels.py --dry-run  # 预览
    python backend/scripts/maintenance/fix_spam_labels.py            # 执行
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from collections import Counter

from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.config import get_settings  # noqa: E402

# 简化版需求关键词
NEED_KEYWORDS = {
    "Survival": {
        "broken", "fail", "scam", "leak", "suspend", "ban", "banned",
        "damage", "defect", "crash", "terrible", "awful", "worst", 
        "hate", "fraud", "fake", "dangerous", "refund", "complaint",
        "problem", "issue", "error", "bug", "warning",
    },
    "Efficiency": {
        "tool", "software", "app", "extension", "plugin", "automate", 
        "bot", "script", "browser", "integration", "api", "workflow",
        "shopify", "klaviyo", "zapier", "notion", "slack", "excel",
    },
    "Belonging": {
        "gift", "friend", "family", "love", "share", "community", "pet",
        "relationship", "together", "birthday", "wedding", "baby",
    },
    "Aesthetic": {
        "beautiful", "gorgeous", "aesthetic", "minimalist", "design",
        "vintage", "elegant", "cute", "pretty", "amazing",
    },
    "Growth": {
        "learn", "guide", "tutorial", "beginner", "course", "income",
        "entrepreneur", "skill", "improve", "success", "strategy", "tips",
        "how to", "startup", "side hustle",
    },
}


def classify_text(text_content: str) -> str:
    """简单关键词分类"""
    text_lower = text_content.lower()
    scores = Counter()
    
    for category, keywords in NEED_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[category] += 1
    
    if scores:
        return scores.most_common(1)[0][0]
    return "Survival"  # 默认


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix Spam labels in post_semantic_labels.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating.")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size.")
    parser.add_argument("--limit", type=int, default=None, help="Max records to process.")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url.replace("asyncpg", "psycopg"), future=True)

    # 获取 Spam 记录
    query = text("""
        SELECT psl.id, psl.post_id, pr.title, pr.body
        FROM post_semantic_labels psl
        JOIN posts_raw pr ON psl.post_id = pr.id
        WHERE psl.l1_category = 'Spam'
        ORDER BY psl.id
        LIMIT :limit
    """)

    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": args.limit or 999999}).mappings().all()

    print(f"📊 找到 {len(rows)} 条 Spam 记录需要处理")

    if not rows:
        print("✅ 无需处理")
        return

    category_counts = Counter()
    errors = 0

    for i, row in enumerate(rows):
        try:
            text_content = f"{row['title'] or ''} {row['body'] or ''}"
            new_l1 = classify_text(text_content)
            category_counts[new_l1] += 1
            
            # 所有原 Spam 记录都添加 spam tag
            tags = ["spam"]
            
            if args.dry_run:
                if i < 10:  # 只打印前 10 条
                    print(f"  [{i+1}] post_id={row['post_id']}: Spam -> {new_l1}, tags={tags}")
            else:
                update_sql = text("""
                    UPDATE post_semantic_labels 
                    SET l1_category = :l1, tags = :tags, updated_at = NOW()
                    WHERE id = :id
                """)
                with engine.begin() as up_conn:
                    up_conn.execute(update_sql, {
                        "l1": new_l1,
                        "tags": tags,
                        "id": row["id"],
                    })
                    
                if (i + 1) % args.batch_size == 0:
                    print(f"  ✅ 已处理 {i+1}/{len(rows)}...")
                    
        except Exception as e:
            errors += 1
            print(f"  ❌ Error processing id={row['id']}: {e}")

    print(f"\n📋 处理完成:")
    print(f"  - 总计: {len(rows)}")
    for cat, cnt in category_counts.most_common():
        print(f"    - {cat}: {cnt}")
    print(f"  - 错误: {errors}")
    
    if args.dry_run:
        print("\n⚠️ 这是 DRY RUN，未实际修改数据。去掉 --dry-run 执行。")


if __name__ == "__main__":
    main()
