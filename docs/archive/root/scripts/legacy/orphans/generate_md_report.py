#!/usr/bin/env python3
from __future__ import annotations

"""
直接生成 Markdown 报告的脚本（基于当前数据库与社区池，不依赖旧的任务/候选流程）。
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory


async def generate_report() -> str:
    """从当前数据库汇总核心指标并生成 Markdown 报告。"""
    print("=" * 60)
    print("开始生成市场洞察报告（基于当前数据库）...")
    print("=" * 60)

    async with SessionFactory() as session:
        # T1/T2/T3 分层统计
        tier_sql = sa.text(
            """
            SELECT tier,
                   COUNT(*) AS communities,
                   COALESCE(SUM(daily_posts), 0) AS daily_posts_sum,
                   COALESCE(AVG(semantic_quality_score), 0.0) AS avg_semantic_score
            FROM community_pool
            WHERE is_active = true
            GROUP BY tier
            ORDER BY tier
            """
        )
        tier_rows = (await session.execute(tier_sql)).mappings().all()

        # T1 社区帖子/评论 TOP10（近12个月）
        t1_sql = sa.text(
            """
            WITH t1 AS (
              SELECT regexp_replace(lower(name), '^r/', '') AS sub
              FROM community_pool
              WHERE tier = 'high' AND is_active = true
            ),
            post_stats AS (
              SELECT lower(subreddit) AS sub,
                     COUNT(*) FILTER (WHERE created_at >= now() - interval '12 months') AS posts_12m
              FROM posts_raw
              GROUP BY lower(subreddit)
            ),
            comment_stats AS (
              SELECT lower(subreddit) AS sub,
                     COUNT(*) FILTER (WHERE created_utc >= now() - interval '12 months') AS comments_12m
              FROM comments
              GROUP BY lower(subreddit)
            )
            SELECT t1.sub AS subreddit,
                   COALESCE(p.posts_12m, 0) AS posts_12m,
                   COALESCE(c.comments_12m, 0) AS comments_12m
            FROM t1
            LEFT JOIN post_stats p ON p.sub = t1.sub
            LEFT JOIN comment_stats c ON c.sub = t1.sub
            ORDER BY comments_12m DESC
            LIMIT 10
            """
        )
        t1_rows = (await session.execute(t1_sql)).mappings().all()

        # 痛点标签分布（T1，近12个月）
        pain_sql = sa.text(
            """
            WITH t1 AS (
              SELECT regexp_replace(lower(name), '^r/', '') AS sub
              FROM community_pool
              WHERE tier = 'high' AND is_active = true
            ),
            labeled AS (
              SELECT cl.category, cl.aspect
              FROM content_labels cl
              JOIN comments c ON cl.content_type = 'comment' AND cl.content_id = c.id
              JOIN t1 ON lower(c.subreddit) = t1.sub
              WHERE c.created_utc >= now() - interval '12 months'
            )
            SELECT category, aspect, COUNT(*) AS cnt
            FROM labeled
            GROUP BY category, aspect
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        pain_rows = (await session.execute(pain_sql)).mappings().all()

        # 品牌实体分布（T1，近12个月）
        entity_sql = sa.text(
            """
            WITH t1 AS (
              SELECT regexp_replace(lower(name), '^r/', '') AS sub
              FROM community_pool
              WHERE tier = 'high' AND is_active = true
            ),
            entities AS (
              SELECT ce.entity, ce.entity_type
              FROM content_entities ce
              JOIN comments c ON ce.content_type = 'comment' AND ce.content_id = c.id
              JOIN t1 ON lower(c.subreddit) = t1.sub
              WHERE c.created_utc >= now() - interval '12 months'
            )
            SELECT entity, entity_type, COUNT(*) AS cnt
            FROM entities
            GROUP BY entity, entity_type
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        entity_rows = (await session.execute(entity_sql)).mappings().all()

    # 组装 Markdown 文本
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"# 跨境电商支付解决方案 · 市场洞察报告")
    lines.append("")
    lines.append(f"- 生成时间：{ts}")
    lines.append(f"- 数据来源：当前 PostgreSQL 数据库（reddit_signal_scanner）")
    lines.append(f"- 社区范围：当前社区池（community_pool，按高/中/语义三层）")
    lines.append("")
    lines.append("## 1. 分层社区概览（T1/T2/T3）")
    lines.append("")
    lines.append("| 层级 | 社区数 | 日均帖子总数 | 平均语义质量分 |")
    lines.append("|------|--------|--------------|----------------|")
    for r in tier_rows:
        lines.append(
            f"| {r['tier']} | {int(r['communities'])} | {int(r['daily_posts_sum'])} | {float(r['avg_semantic_score']):.3f} |"
        )

    lines.append("")
    lines.append("## 2. T1 高价值社区 · 帖子与评论量（近 12 个月）")
    lines.append("")
    lines.append("| 社区 | 12 月帖子数 | 12 月评论数 |")
    lines.append("|------|-------------|-------------|")
    for r in t1_rows:
        lines.append(
            f"| r/{r['subreddit']} | {int(r['posts_12m'])} | {int(r['comments_12m'])} |"
        )

    lines.append("")
    lines.append("## 3. T1 高价值社区 · 痛点标签分布（近 12 个月）")
    lines.append("")
    lines.append("| 类别 | 维度 | 标签数量 |")
    lines.append("|------|------|----------|")
    for r in pain_rows:
        lines.append(f"| {r['category']} | {r['aspect']} | {int(r['cnt'])} |")

    lines.append("")
    lines.append("## 4. T1 高价值社区 · 品牌/平台实体分布（近 12 个月）")
    lines.append("")
    lines.append("| 实体 | 类型 | 命中次数 |")
    lines.append("|------|------|----------|")
    for r in entity_rows:
        lines.append(f"| {r['entity']} | {r['entity_type']} | {int(r['cnt'])} |")

    markdown_content = "\n".join(lines)

    # 保存到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = BACKEND_ROOT / "reports" / "generated" / f"market_report_{timestamp}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_content, encoding="utf-8")

    print("\n" + "=" * 60)
    print("✅ 报告生成成功！")
    print(f"📄 文件位置: {output_path}")
    print(f"📊 报告大小: {len(markdown_content):,} 字符")
    print("=" * 60)

    print("\n报告预览（前 500 字符）:")
    print("-" * 60)
    print(markdown_content[:500])
    print("-" * 60)

    return str(output_path)


if __name__ == "__main__":
    try:
        path = asyncio.run(generate_report())
        print(f"\n💡 查看完整报告: cat {path}")
    except Exception as exc:  # pragma: no cover - CLI 兜底
        print(f"\n❌ 报告生成失败: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
