#!/usr/bin/env python3
"""
抽样 200 条帖子用于人工标注

基于 Spec 007 User Story 5 (US5) - Task T052
从 posts_raw 表中抽样 200 条帖子，用于阈值校准的人工标注

抽样策略：
1. 只抽取最近 30 天的帖子（保证时效性）
2. 只抽取 is_current=True 的帖子（最新版本）
3. 按 score 分层抽样：高分（50条）、中分（100条）、低分（50条）
4. 确保多样性：覆盖不同 subreddit

用法:
    python scripts/sample_posts_for_annotation.py
    python scripts/sample_posts_for_annotation.py --output data/annotations/sample_200.csv
"""
import asyncio
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_context
from app.models.posts_storage import PostRaw


async def sample_posts(
    *,
    total_samples: int = 200,
    days_back: int = 30,
    high_score_threshold: int = 100,
    low_score_threshold: int = 10,
) -> List[PostRaw]:
    """从数据库中抽样帖子
    
    Args:
        total_samples: 总抽样数量（默认 200）
        days_back: 抽样时间范围（默认最近 30 天）
        high_score_threshold: 高分阈值（默认 100）
        low_score_threshold: 低分阈值（默认 10）
    
    Returns:
        List[PostRaw]: 抽样的帖子列表
    """
    async with get_session_context() as session:
        # 计算时间范围
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # 分层抽样数量
        high_score_count = int(total_samples * 0.25)  # 25% 高分
        mid_score_count = int(total_samples * 0.50)   # 50% 中分
        low_score_count = total_samples - high_score_count - mid_score_count  # 25% 低分
        
        # 基础查询条件（排除测试数据）
        base_query = (
            select(PostRaw)
            .where(
                PostRaw.is_current.is_(True),
                PostRaw.created_at >= cutoff_date,
                PostRaw.title.isnot(None),
                PostRaw.title != "",
                ~PostRaw.subreddit.like('r/test_%'),  # 排除测试数据
            )
        )
        
        # 1. 抽样高分帖子（score >= high_score_threshold）
        high_score_query = (
            base_query
            .where(PostRaw.score >= high_score_threshold)
            .order_by(func.random())
            .limit(high_score_count)
        )
        high_score_posts = (await session.execute(high_score_query)).scalars().all()
        
        # 2. 抽样中分帖子（low_score_threshold <= score < high_score_threshold）
        mid_score_query = (
            base_query
            .where(
                PostRaw.score >= low_score_threshold,
                PostRaw.score < high_score_threshold,
            )
            .order_by(func.random())
            .limit(mid_score_count)
        )
        mid_score_posts = (await session.execute(mid_score_query)).scalars().all()
        
        # 3. 抽样低分帖子（score < low_score_threshold）
        low_score_query = (
            base_query
            .where(PostRaw.score < low_score_threshold)
            .order_by(func.random())
            .limit(low_score_count)
        )
        low_score_posts = (await session.execute(low_score_query)).scalars().all()
        
        # 合并所有抽样结果
        all_posts = list(high_score_posts) + list(mid_score_posts) + list(low_score_posts)
        
        print(f"✅ 抽样完成:")
        print(f"   - 高分帖子 (score >= {high_score_threshold}): {len(high_score_posts)} 条")
        print(f"   - 中分帖子 ({low_score_threshold} <= score < {high_score_threshold}): {len(mid_score_posts)} 条")
        print(f"   - 低分帖子 (score < {low_score_threshold}): {len(low_score_posts)} 条")
        print(f"   - 总计: {len(all_posts)} 条")
        
        return all_posts


def export_to_csv(posts: List[PostRaw], output_path: Path):
    """导出帖子到 CSV 文件
    
    Args:
        posts: 帖子列表
        output_path: 输出文件路径
    """
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入 CSV
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "subreddit",
                "title",
                "body",
                "score",
                "num_comments",
                "created_at",
                "url",
                "label",
                "strength",
                "notes",
            ],
        )
        writer.writeheader()
        
        for post in posts:
            # 构造 Reddit URL
            reddit_url = post.url or f"https://reddit.com/r/{post.subreddit}/comments/{post.source_post_id}"
            
            writer.writerow({
                "post_id": post.source_post_id,
                "subreddit": post.subreddit,
                "title": post.title,
                "body": (post.body or "")[:500],  # 限制 body 长度，避免 CSV 过大
                "score": post.score,
                "num_comments": post.num_comments,
                "created_at": post.created_at.isoformat() if post.created_at else "",
                "url": reddit_url,
                "label": "",  # 待人工标注
                "strength": "",  # 待人工标注
                "notes": "",  # 待人工标注
            })
    
    print(f"✅ 已导出到: {output_path}")
    print(f"   - 文件大小: {output_path.stat().st_size / 1024:.2f} KB")


async def main():
    """主函数"""
    import argparse

    # 获取项目根目录（backend 的父目录）
    project_root = backend_dir.parent
    default_output = project_root / "data" / "annotations" / "sample_200.csv"

    parser = argparse.ArgumentParser(description="抽样帖子用于人工标注")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"输出 CSV 文件路径（默认: {default_output}）",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="抽样数量（默认: 200）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="抽样时间范围（天数，默认: 30）",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("📊 抽样帖子用于人工标注")
    print("=" * 80)
    print()
    print(f"📋 配置:")
    print(f"   - 抽样数量: {args.count}")
    print(f"   - 时间范围: 最近 {args.days} 天")
    print(f"   - 输出文件: {args.output}")
    print()
    
    # 抽样帖子
    posts = await sample_posts(
        total_samples=args.count,
        days_back=args.days,
    )
    
    if not posts:
        print("❌ 未找到符合条件的帖子")
        return 1
    
    # 导出到 CSV
    export_to_csv(posts, args.output)
    
    print()
    print("=" * 80)
    print("✅ 抽样完成")
    print("=" * 80)
    print()
    print("📝 下一步:")
    print(f"   1. 打开文件: {args.output}")
    print("   2. 人工标注 label 列（opportunity / non-opportunity）")
    print("   3. 人工标注 strength 列（strong / medium / weak）")
    print("   4. 可选：在 notes 列添加备注")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

