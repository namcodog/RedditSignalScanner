#!/usr/bin/env python3
"""
🎯 Focused Rant Hunter - 定向爆帖猎手

在特定社区内搜索吐槽帖，避免全站搜索的噪音问题。

用法：
    python backend/scripts/hunt_rant_focused.py --brand "Roomba" --subreddits "roomba,RobotVacuums"
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
from typing import Any, Dict, List

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient, RedditPost

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# 吐槽触发词
RANT_TRIGGERS = [
    "broken",
    "problem",
    "issue",
    "terrible",
    "worst",
    "hate",
    "regret",
    "refund",
    "disappointed",
    "avoid",
    "returned",
    "not working",
    "stopped",
    "error",
    "defective",
    "waste",
    "garbage",
    "useless",
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
    permalink: str
    created_utc: float
    top_comments: List[Dict[str, Any]] = field(default_factory=list)
    rant_signals: List[str] = field(default_factory=list)
    
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
    
    @property
    def rant_score(self) -> float:
        """吐槽强度 = 吐槽信号数 * 10 + 热度"""
        return len(self.rant_signals) * 10 + self.heat_score * 0.01


def detect_rant_signals(title: str, body: str) -> List[str]:
    """检测帖子中的吐槽信号词"""
    text = f"{title} {body}".lower()
    found = []
    for trigger in RANT_TRIGGERS:
        if trigger in text:
            found.append(trigger)
    return found


async def hunt_in_subreddit(
    client: RedditAPIClient,
    subreddit: str,
    *,
    query: str = "",
    time_filter: str = "all",
    max_posts: int = 200,
) -> List[RedditPost]:
    """在单个社区内搜索帖子"""
    posts: List[RedditPost] = []
    after: str | None = None
    
    try:
        # 如果没有 query，搜所有帖子
        search_query = query if query else "*"
        
        while len(posts) < max_posts:
            batch, after = await client.search_subreddit_page(
                subreddit,
                search_query,
                limit=100,
                sort="top",
                time_filter=time_filter,
                restrict_sr=1,
                syntax=None,  # 用普通搜索语法
                after=after,
            )
            if not batch:
                break
            posts.extend(batch)
            if not after:
                break
    except Exception as e:
        log.warning(f"搜索 r/{subreddit} 失败: {e}")
    
    return posts[:max_posts]


async def hunt_focused(
    *,
    brand: str,
    subreddits: List[str],
    time_filter: str = "all",
    max_posts_per_sub: int = 200,
    top_n: int = 30,
    min_comments: int = 3,
) -> Dict[str, Any]:
    """
    在指定社区内搜索吐槽帖
    """
    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=30,
        rate_limit_window=60.0,
        request_timeout=30.0,
        max_concurrency=3,
    )
    
    all_posts: List[RedditPost] = []
    
    log.info(f"🎯 开始在 {len(subreddits)} 个社区中搜索 [{brand}] 的吐槽帖")
    
    async with client:
        # Step 1: 在每个社区搜索
        for sr in subreddits:
            log.info(f"  📍 搜索社区 r/{sr}...")
            posts = await hunt_in_subreddit(
                client,
                sr,
                query=brand,
                time_filter=time_filter,
                max_posts=max_posts_per_sub,
            )
            log.info(f"     ↳ 获取 {len(posts)} 条帖子")
            all_posts.extend(posts)
        
        log.info(f"📊 总计收集 {len(all_posts)} 条帖子")
        
        # Step 2: 检测吐槽信号并过滤
        rant_posts: List[RantPost] = []
        for p in all_posts:
            signals = detect_rant_signals(p.title, p.selftext or "")
            if signals and p.num_comments >= min_comments:
                rant_posts.append(RantPost(
                    id=p.id,
                    title=p.title,
                    body=(p.selftext or "")[:1000],
                    score=p.score,
                    num_comments=p.num_comments,
                    subreddit=p.subreddit,
                    author=p.author,
                    permalink=p.permalink,
                    created_utc=p.created_utc,
                    rant_signals=signals,
                ))
        
        # 按吐槽强度排序
        rant_posts.sort(key=lambda x: x.rant_score, reverse=True)
        rant_posts = rant_posts[:top_n]
        
        log.info(f"🔥 筛选出 {len(rant_posts)} 条吐槽帖（有吐槽信号 + 评论≥{min_comments}）")
        
        # Step 3: 抓取评论
        for idx, rp in enumerate(rant_posts[:20]):  # 只抓前20条的评论
            log.info(f"  💬 [{idx+1}/{min(20, len(rant_posts))}] 抓评论: {rp.title[:50]}...")
            try:
                comments = await client.fetch_post_comments(
                    rp.id,
                    sort="top",
                    limit=3,
                    mode="topn",
                )
                rp.top_comments = [
                    {
                        "author": c.get("author", "unknown"),
                        "body": c.get("body", "")[:400],
                        "score": c.get("score", 0),
                    }
                    for c in comments[:3]
                ]
            except Exception as e:
                log.warning(f"     ⚠️ 评论抓取失败: {e}")
    
    return {
        "brand": brand,
        "subreddits_searched": subreddits,
        "total_posts_scanned": len(all_posts),
        "rant_posts_found": len(rant_posts),
        "hunt_time": datetime.now().isoformat(),
        "top_rants": rant_posts,
    }


def export_results(result: Dict[str, Any], output_dir: Path, brand_slug: str) -> None:
    """导出 JSON 和 Markdown"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    json_path = output_dir / f"{brand_slug}_focused_evidence.json"
    json_data = {
        "meta": {
            "brand": result["brand"],
            "subreddits_searched": result["subreddits_searched"],
            "total_posts_scanned": result["total_posts_scanned"],
            "rant_posts_found": result["rant_posts_found"],
            "hunt_time": result["hunt_time"],
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
                "rant_score": round(rp.rant_score, 2),
                "rant_signals": rp.rant_signals,
                "subreddit": rp.subreddit,
                "author": rp.author,
                "reddit_url": rp.reddit_url,
                "created_utc": rp.created_utc,
                "top_comments": rp.top_comments,
            }
            for idx, rp in enumerate(result["top_rants"])
        ],
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"📁 JSON: {json_path}")
    
    # Markdown
    md_path = output_dir / f"{brand_slug}_focused_report.md"
    lines = [
        f"# 🎯 {result['brand']} 定向吐槽挖掘报告",
        "",
        f"**生成时间**: {result['hunt_time']}",
        f"**搜索社区**: {', '.join(['r/' + s for s in result['subreddits_searched']])}",
        f"**扫描帖子**: {result['total_posts_scanned']} 条",
        f"**吐槽帖子**: {result['rant_posts_found']} 条",
        "",
        "---",
        "",
        "## 🔥 Top 吐槽帖排行",
        "",
    ]
    
    for idx, rp in enumerate(result["top_rants"][:15]):
        lines.append(f"### #{idx+1} [{rp.title}]({rp.reddit_url})")
        lines.append("")
        lines.append(f"- **社区**: r/{rp.subreddit}")
        lines.append(f"- **点赞**: {rp.score} | **评论**: {rp.num_comments} | **吐槽分**: {rp.rant_score:.1f}")
        lines.append(f"- **吐槽信号**: {', '.join(rp.rant_signals)}")
        lines.append("")
        
        if rp.body:
            lines.append(f"> {rp.body[:250]}...")
            lines.append("")
        
        if rp.top_comments:
            lines.append("**🗣️ 精选评论:**")
            lines.append("")
            for cidx, c in enumerate(rp.top_comments[:2]):
                comment_text = c['body'].replace('\n', ' ')[:150]
                lines.append(f"{cidx+1}. [👍 {c['score']}] **u/{c['author']}**: {comment_text}...")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    md_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"📁 Markdown: {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="🎯 Focused Rant Hunter - 定向吐槽猎手")
    parser.add_argument("--brand", type=str, required=True, help="目标品牌名")
    parser.add_argument("--subreddits", type=str, required=True, help="目标社区，逗号分隔")
    parser.add_argument("--time-filter", type=str, default="all", help="时间范围")
    parser.add_argument("--max-posts", type=int, default=200, help="每社区最多抓取")
    parser.add_argument("--top-n", type=int, default=30, help="输出 Top N 帖子")
    parser.add_argument("--min-comments", type=int, default=3, help="最低评论数")
    parser.add_argument("--output-dir", type=str, default="reports/rant-hunter", help="输出目录")
    args = parser.parse_args()
    
    subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    
    result = asyncio.run(hunt_focused(
        brand=args.brand,
        subreddits=subreddits,
        time_filter=args.time_filter,
        max_posts_per_sub=args.max_posts,
        top_n=args.top_n,
        min_comments=args.min_comments,
    ))
    
    output_dir = Path(args.output_dir)
    brand_slug = args.brand.lower().replace(" ", "_")
    export_results(result, output_dir, brand_slug)
    
    # 终端摘要
    print("\n" + "=" * 60)
    print(f"🎯 {result['brand']} 定向吐槽挖掘完成！")
    print(f"   搜索社区: {', '.join(['r/' + s for s in result['subreddits_searched']])}")
    print(f"   扫描帖子: {result['total_posts_scanned']} 条")
    print(f"   吐槽帖子: {result['rant_posts_found']} 条")
    print("=" * 60)
    
    print(f"\n📊 Top 5 吐槽帖预览:\n")
    for idx, rp in enumerate(result["top_rants"][:5]):
        print(f"  {idx+1}. [{rp.score}👍 {rp.num_comments}💬] {rp.title[:55]}...")
        print(f"     🔥 吐槽信号: {', '.join(rp.rant_signals[:3])}")
        print(f"     🔗 {rp.reddit_url}")
        print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
