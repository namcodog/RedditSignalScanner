#!/usr/bin/env python3
"""
🔥 Rant Post Hunter - 爆帖猎手

快速验证脚本：通过关键词搜索 Reddit 上的极端吐槽帖子，输出证据包。

用法：
    python backend/scripts/hunt_rant_posts.py --brand "iRobot"
    python backend/scripts/hunt_rant_posts.py --brand "Adobe" --time-filter year
    python backend/scripts/hunt_rant_posts.py --brand "Salesforce" --rant-words "bug,nightmare,terrible"

输出：
    1. JSON 证据包（帖子 + 评论 + 社区统计）
    2. Markdown 报告（人类可读）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import get_settings
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# 默认的吐槽触发词（英文环境）
DEFAULT_RANT_WORDS = [
    "nightmare",
    "terrible",
    "worst",
    "broken",
    "hate",
    "leaving",
    "refund",
    "waste of money",
    "avoid",
    "disappointed",
    "regret",
    "garbage",
    "trash",
    "scam",
    "rip off",
]


@dataclass
class RantPost:
    """一条爆帖的结构化表示"""
    id: str
    title: str
    body: str
    score: int
    num_comments: int
    subreddit: str
    author: str
    url: str
    permalink: str
    created_utc: float
    top_comments: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def reddit_url(self) -> str:
        # Handle cases where permalink already has full URL
        if self.permalink.startswith("http"):
            return self.permalink
        return f"https://reddit.com{self.permalink}"
    
    @property
    def heat_score(self) -> float:
        """热度分 = 赞 + 评论数 * 2（评论权重更高）"""
        return float(self.score + self.num_comments * 2)


@dataclass
class HuntResult:
    """猎手结果：帖子 + 社区统计"""
    brand: str
    query_count: int
    total_posts_scanned: int
    top_rants: List[RantPost]
    community_stats: Dict[str, int]  # {subreddit: count}
    query_list: List[str]
    hunt_time: str


def build_queries(brand: str, rant_words: List[str]) -> List[str]:
    """构建搜索查询组合"""
    queries = []
    # 品牌 + 吐槽词
    for word in rant_words[:10]:  # 限制组合数量
        queries.append(f'{brand} {word}')
    # 纯品牌（兜底）
    queries.append(brand)
    return queries


async def hunt_rant_posts(
    *,
    brand: str,
    rant_words: List[str],
    time_filter: str = "all",
    sort: str = "top",
    max_posts: int = 50,
    min_score: int = 50,
    min_comments: int = 10,
    top_comments_limit: int = 3,
) -> HuntResult:
    """
    主猎手逻辑：搜索 + 过滤 + 抓评论
    """
    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=30,  # 保守一点
        rate_limit_window=60.0,
        request_timeout=30.0,
        max_concurrency=3,
    )
    
    queries = build_queries(brand, rant_words)
    all_posts: Dict[str, RedditPost] = {}  # 去重用
    community_counts: Dict[str, int] = defaultdict(int)
    
    log.info(f"🎯 开始猎杀 [{brand}] 的爆帖，共 {len(queries)} 个查询组合")
    
    async with client:
        # Step 1: 搜索帖子
        for query in queries:
            try:
                log.info(f"  🔍 搜索: {query}")
                posts = await client.search_posts(
                    query,
                    limit=100,
                    time_filter=time_filter,
                    sort=sort,
                )
                for p in posts:
                    if p.id not in all_posts:
                        all_posts[p.id] = p
                        community_counts[p.subreddit] += 1
                log.info(f"     ↳ 命中 {len(posts)} 条，累计 {len(all_posts)} 条去重帖")
            except Exception as e:
                log.warning(f"     ⚠️ 查询失败: {e}")
                continue
        
        log.info(f"📊 总计扫描 {len(all_posts)} 条帖子")
        
        # Step 2: 过滤高热度帖子
        hot_posts = [
            p for p in all_posts.values()
            if p.score >= min_score or p.num_comments >= min_comments
        ]
        hot_posts.sort(key=lambda p: p.score + p.num_comments * 2, reverse=True)
        hot_posts = hot_posts[:max_posts]
        
        log.info(f"🔥 筛选出 {len(hot_posts)} 条高热度帖子（score≥{min_score} 或 comments≥{min_comments}）")
        
        # Step 3: 抓取每个帖子的 Top 评论
        rant_posts: List[RantPost] = []
        for idx, p in enumerate(hot_posts):
            log.info(f"  💬 [{idx+1}/{len(hot_posts)}] 抓取评论: {p.title[:50]}...")
            try:
                comments = await client.fetch_post_comments(
                    p.id,
                    sort="top",
                    limit=top_comments_limit,
                    mode="topn",
                )
                top_comments = [
                    {
                        "author": c.get("author", "unknown"),
                        "body": c.get("body", "")[:500],  # 截断
                        "score": c.get("score", 0),
                    }
                    for c in comments[:top_comments_limit]
                ]
            except Exception as e:
                log.warning(f"     ⚠️ 评论抓取失败: {e}")
                top_comments = []
            
            rant_posts.append(RantPost(
                id=p.id,
                title=p.title,
                body=(p.selftext or "")[:1000],
                score=p.score,
                num_comments=p.num_comments,
                subreddit=p.subreddit,
                author=p.author,
                url=p.url,
                permalink=p.permalink,
                created_utc=p.created_utc,
                top_comments=top_comments,
            ))
    
    return HuntResult(
        brand=brand,
        query_count=len(queries),
        total_posts_scanned=len(all_posts),
        top_rants=rant_posts,
        community_stats=dict(sorted(community_counts.items(), key=lambda x: x[1], reverse=True)),
        query_list=queries,
        hunt_time=datetime.now().isoformat(),
    )


def export_json(result: HuntResult, output_path: Path) -> None:
    """导出 JSON 证据包"""
    payload = {
        "meta": {
            "brand": result.brand,
            "hunt_time": result.hunt_time,
            "query_count": result.query_count,
            "total_posts_scanned": result.total_posts_scanned,
            "queries_used": result.query_list,
        },
        "top_rants": [
            {
                "rank": idx + 1,
                "id": rp.id,
                "title": rp.title,
                "body_preview": rp.body[:300] if rp.body else "",
                "score": rp.score,
                "num_comments": rp.num_comments,
                "heat_score": rp.heat_score,
                "subreddit": rp.subreddit,
                "author": rp.author,
                "reddit_url": rp.reddit_url,
                "created_utc": rp.created_utc,
                "top_comments": rp.top_comments,
            }
            for idx, rp in enumerate(result.top_rants)
        ],
        "community_stats": result.community_stats,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"📁 JSON 已保存: {output_path}")


def export_markdown(result: HuntResult, output_path: Path) -> None:
    """导出 Markdown 报告"""
    lines = [
        f"# 🔥 {result.brand} 爆帖猎杀报告",
        "",
        f"**生成时间**: {result.hunt_time}",
        f"**扫描帖子数**: {result.total_posts_scanned}",
        f"**高热度帖子数**: {len(result.top_rants)}",
        "",
        "---",
        "",
        "## 🏆 Top 爆帖排行",
        "",
    ]
    
    for idx, rp in enumerate(result.top_rants[:10]):
        lines.append(f"### #{idx+1} [{rp.title}]({rp.reddit_url})")
        lines.append("")
        lines.append(f"- **社区**: r/{rp.subreddit}")
        lines.append(f"- **点赞**: {rp.score} | **评论数**: {rp.num_comments} | **热度分**: {rp.heat_score:.0f}")
        lines.append(f"- **作者**: u/{rp.author}")
        lines.append("")
        
        if rp.body:
            lines.append(f"> {rp.body[:200]}...")
            lines.append("")
        
        if rp.top_comments:
            lines.append("**🗣️ 神评论:**")
            lines.append("")
            for cidx, c in enumerate(rp.top_comments[:2]):
                lines.append(f"{cidx+1}. [👍 {c['score']}] **u/{c['author']}**: {c['body'][:150]}...")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # 社区统计
    lines.append("## 📊 社区分布（帖子来源）")
    lines.append("")
    lines.append("| 社区 | 帖子数 |")
    lines.append("|------|--------|")
    for sr, cnt in list(result.community_stats.items())[:15]:
        lines.append(f"| r/{sr} | {cnt} |")
    lines.append("")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"📁 Markdown 已保存: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="🔥 Rant Post Hunter - 爆帖猎手")
    parser.add_argument("--brand", type=str, required=True, help="目标品牌名（如 iRobot, Adobe）")
    parser.add_argument("--rant-words", type=str, default=None, help="吐槽词，逗号分隔（可选，有默认值）")
    parser.add_argument("--time-filter", type=str, default="all", help="时间范围: hour/day/week/month/year/all")
    parser.add_argument("--sort", type=str, default="top", help="排序: top/relevance/comments/new")
    parser.add_argument("--max-posts", type=int, default=30, help="最多抓取多少条高热度帖子")
    parser.add_argument("--min-score", type=int, default=30, help="最低点赞数")
    parser.add_argument("--min-comments", type=int, default=10, help="最低评论数")
    parser.add_argument("--output-dir", type=str, default="backend/reports/rant-hunter", help="输出目录")
    args = parser.parse_args()
    
    rant_words = (
        [w.strip() for w in args.rant_words.split(",") if w.strip()]
        if args.rant_words
        else DEFAULT_RANT_WORDS
    )
    
    result = asyncio.run(hunt_rant_posts(
        brand=args.brand,
        rant_words=rant_words,
        time_filter=args.time_filter,
        sort=args.sort,
        max_posts=args.max_posts,
        min_score=args.min_score,
        min_comments=args.min_comments,
    ))
    
    # 输出文件
    output_dir = Path(args.output_dir)
    brand_slug = args.brand.lower().replace(" ", "_")
    json_path = output_dir / f"{brand_slug}_rant_evidence.json"
    md_path = output_dir / f"{brand_slug}_rant_report.md"
    
    export_json(result, json_path)
    export_markdown(result, md_path)
    
    # 终端摘要
    print("\n" + "=" * 60)
    print(f"🎯 {result.brand} 爆帖猎杀完成！")
    print(f"   扫描帖子: {result.total_posts_scanned} 条")
    print(f"   高热度帖子: {len(result.top_rants)} 条")
    print(f"   涉及社区: {len(result.community_stats)} 个")
    print("=" * 60)
    print(f"\n📊 Top 5 爆帖预览:\n")
    for idx, rp in enumerate(result.top_rants[:5]):
        print(f"  {idx+1}. [{rp.score}👍 {rp.num_comments}💬] {rp.title[:60]}...")
        print(f"     🔗 {rp.reddit_url}")
        print()
    print(f"📁 完整报告: {md_path}")
    print(f"📁 JSON 数据: {json_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
