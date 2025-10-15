#!/usr/bin/env python
"""
在 Redis 中预置 Reddit 帖子缓存，支撑 Day 9 信号回归验证。

用途：
1. 解决开发/测试环境无法访问真实 Reddit API 时的缓存空洞问题
2. 保障信号提取阶段至少返回痛点≥5、竞品≥3、机会≥3
3. 与 `docs/PRD/PRD-03-分析引擎.md` 的缓存优先策略保持一致

使用示例：
    python backend/scripts/seed_test_data.py          # 写入默认测试数据
    python backend/scripts/seed_test_data.py --purge  # 清理脚本生成的数据
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.cache_manager import CacheManager  # noqa: E402
from app.services.reddit_client import RedditPost  # noqa: E402


def _minutes_ago(minutes: int) -> float:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp()


def _make_post(
    subreddit: str,
    slug: str,
    *,
    title: str,
    body: str,
    score: int,
    comments: int,
    minutes_ago: int,
) -> RedditPost:
    subreddit_clean = subreddit.lstrip("/")
    return RedditPost(
        id=f"{subreddit_clean}-{slug}",
        title=title,
        selftext=body,
        score=score,
        num_comments=comments,
        created_utc=_minutes_ago(minutes_ago),
        subreddit=subreddit_clean,
        author="seed-bot",
        url=f"https://reddit.com/{subreddit_clean}/{slug}",
        permalink=f"/{subreddit_clean}/{slug}",
    )


SEED_POSTS: Dict[str, List[RedditPost]] = {
    "r/artificial": [
        _make_post(
            "r/artificial",
            "pain-slow-onboarding",
            title="Users can't stand how slow the onboarding flow is",
            body="I can't stand how painfully slow the onboarding workflow feels when scaling AI research teams.",
            score=215,
            comments=32,
            minutes_ago=35,
        ),
        _make_post(
            "r/artificial",
            "pain-confusing-export",
            title="Why is export still so confusing for research ops?",
            body="Why is export so confusing and unreliable even after the latest release? It still feels broken.",
            score=180,
            comments=24,
            minutes_ago=58,
        ),
        _make_post(
            "r/artificial",
            "competitor-notion-vs-evernote",
            title="Notion vs Evernote for research automation?",
            body="Notion vs Evernote showdown: which platform actually handles automation without becoming too expensive?",
            score=140,
            comments=19,
            minutes_ago=110,
        ),
        _make_post(
            "r/artificial",
            "opportunity-looking-for-automation",
            title="Looking for an automation tool that would pay for itself",
            body="Our lab is looking for an automation tool that would pay for itself with better weekly insight digests.",
            score=125,
            comments=11,
            minutes_ago=160,
        ),
        _make_post(
            "r/artificial",
            "opportunity-need-leadership-updates",
            title="Need a simple way to keep leadership updated",
            body="Need a simple way to keep leadership updated with AI project summaries without manual spreadsheets.",
            score=105,
            comments=9,
            minutes_ago=210,
        ),
    ],
    "r/startups": [
        _make_post(
            "r/startups",
            "pain-cant-believe-export",
            title="Can't believe the export workflow is still broken",
            body="I can't believe export still doesn't work for our startup clients—it's expensive and unreliable.",
            score=198,
            comments=27,
            minutes_ago=48,
        ),
        _make_post(
            "r/startups",
            "pain-slow-customer-onboarding",
            title="Customer onboarding remains painfully slow",
            body="Our onboarding is painfully slow and confusing; customers hate the complex steps.",
            score=155,
            comments=17,
            minutes_ago=95,
        ),
        _make_post(
            "r/startups",
            "competitor-linear-vs-jira",
            title="Linear vs Jira as an alternative to handle product feedback",
            body="We're comparing Linear versus Jira as an alternative to manage product feedback workflows.",
            score=130,
            comments=14,
            minutes_ago=150,
        ),
        _make_post(
            "r/startups",
            "opportunity-wish-for-platform",
            title="Wish there was a workflow platform focused on reporting",
            body="Wish there was a workflow platform that pays for itself with weekly reporting automation for founders.",
            score=118,
            comments=10,
            minutes_ago=190,
        ),
    ],
    "r/ProductManagement": [
        _make_post(
            "r/ProductManagement",
            "pain-struggle-insights",
            title="Struggling to collect reliable customer insights",
            body="We struggle to collect reliable insights because the research export pipeline is too slow and unreliable.",
            score=165,
            comments=21,
            minutes_ago=60,
        ),
        _make_post(
            "r/ProductManagement",
            "pain-problem-with-automation",
            title="Problem with automation quality in customer reports",
            body="Problem with automation quality: the generated reports feel confusing and frustrating for stakeholders.",
            score=142,
            comments=16,
            minutes_ago=120,
        ),
        _make_post(
            "r/ProductManagement",
            "competitor-amplitude-vs-mixpanel",
            title="Amplitude vs Mixpanel when compared to traditional dashboards",
            body="Amplitude versus Mixpanel compared to legacy dashboards—looking for an alternative to handle opportunity scoring.",
            score=128,
            comments=13,
            minutes_ago=170,
        ),
        _make_post(
            "r/ProductManagement",
            "opportunity-would-love-weekly-digest",
            title="Would love a weekly digest automation for execs",
            body="Would love an automation that delivers confident weekly digests so executives stay informed without manual prep.",
            score=119,
            comments=11,
            minutes_ago=220,
        ),
    ],
}


def _seed(cache: CacheManager) -> None:
    for subreddit, posts in SEED_POSTS.items():
        cache.set_cached_posts(subreddit, posts)
        print(f"✅ Seeded {len(posts)} post(s) for {subreddit}")

    keys = cache.redis.keys(f"{cache.namespace}:*")
    print(f"\n📦 Redis keys under namespace '{cache.namespace}': {len(keys)}")
    for key in keys:
        print(f"   - {key.decode('utf-8') if isinstance(key, bytes) else key}")


def _purge(cache: CacheManager) -> None:
    keys: Iterable[bytes] = cache.redis.keys(f"{cache.namespace}:*")
    deleted = 0
    for key in keys:
        cache.redis.delete(key)
        deleted += 1
    print(f"🧹 Purged {deleted} cached subreddit payload(s) from namespace '{cache.namespace}'.")


def main() -> int:
    parser = argparse.ArgumentParser(description="向 Redis 写入或清理 Reddit 缓存测试数据。")
    parser.add_argument(
        "--redis-url",
        default=None,
        help="Redis 连接串，默认读取设置中的 REDDIT_CACHE_REDIS_URL。",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="删除脚本生成的数据，而不是写入测试数据。",
    )
    args = parser.parse_args()

    settings = get_settings()
    redis_url = args.redis_url or settings.reddit_cache_redis_url
    cache = CacheManager(redis_url=redis_url)

    if args.purge:
        _purge(cache)
    else:
        _seed(cache)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
