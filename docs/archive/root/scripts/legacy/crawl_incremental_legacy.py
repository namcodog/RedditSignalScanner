#!/usr/bin/env python3
"""
[LEGACY] 非生产脚本 / OFFLINE TOOL ONLY
----------------------------------------
此脚本仅用于【离线批量抓取】或【冷启动回填】。
它生成的 JSONL 文件不会自动入库，且抓取过程**不包含**业务层的垃圾过滤逻辑。

- 生产环境请使用 Celery 调度 (System A)。
- 抓取结果需配合 `ingest_jsonl.py` 导入数据库。

增量抓取脚本（/new + 水位线）
用途：
- 每天/每周期抓取最新帖子，直到遇到水位线（last_seen_created_utc）或达到页数上限
- 结果流式写入 JSONL，更新水位线文件与 KPI 报表

水位线存储（无数据库模式）：
- 路径：backend/data/reddit_corpus/waterline/<subreddit>.json
- 字段：last_seen_created_utc, last_seen_post_id, updated_at

示例：
  python backend/scripts/crawl_incremental.py \
    --subreddit ecommerce \
    --max-pages 10 \
    --lookback-days 7 \
    --output backend/data/reddit_corpus/ecommerce.jsonl \
    --stream-write
"""
from __future__ import annotations

import argparse
import json
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient


@dataclass
class Submission:
    id: str
    title: str
    selftext: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    author: str
    url: str
    permalink: str


class JSONLWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = self.path.open("a", encoding="utf-8")

    def write_record(self, rec: Submission) -> None:
        self._f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self) -> None:
        try:
            self._f.close()
        except Exception:
            pass


def _waterline_path(subreddit: str) -> Path:
    return Path("backend/data/reddit_corpus/waterline") / f"{subreddit}.json"


def _load_waterline(subreddit: str) -> Dict[str, Any]:
    p = _waterline_path(subreddit)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_waterline(subreddit: str, last_created: float, last_id: str) -> None:
    p = _waterline_path(subreddit)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_seen_created_utc": float(last_created),
        "last_seen_post_id": str(last_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _kpi_path() -> Path:
    return Path("backend/reports/local-acceptance/incremental_kpi.csv")


def _append_kpi(**row: Any) -> None:
    p = _kpi_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "ts",
        "subreddit",
        "new_posts",
        "pages",
        "stop_reason",
    ]
    line = ",".join(
        [
            datetime.now(timezone.utc).isoformat(),
            str(row.get("subreddit", "")),
            str(row.get("new_posts", 0)),
            str(row.get("pages", 0)),
            str(row.get("stop_reason", "")),
        ]
    )
    if not p.exists():
        p.write_text(",".join(header) + "\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _progress_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".progress.json")


def _write_progress(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def crawl_incremental(
    subreddit: str,
    *,
    output: Path,
    max_pages: int,
    lookback_days: int,
    stream_write: bool,
) -> Dict[str, Any]:
    settings = get_settings()
    last = _load_waterline(subreddit)
    last_created = float(last.get("last_seen_created_utc") or 0.0)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=max(1, lookback_days))
    ).timestamp()
    # 如果没有水位线，使用 lookback 天为初始阈值
    if last_created <= 0:
        last_created = cutoff

    writer = JSONLWriter(output) if stream_write else None
    progress = _progress_path(output)
    _write_progress(progress, {
        "subreddit": subreddit,
        "status": "initialized",
        "last_seen_created_utc": last_created,
        "pages": 0,
        "new_posts": 0,
    })

    async with RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        max_concurrency=min(2, settings.reddit_max_concurrency),
    ) as api:
        await api.authenticate()
        pages = 0
        total_new = 0
        max_seen_created = last_created
        last_id = last.get("last_seen_post_id") or ""
        after: Optional[str] = None
        stop_reason = "exhausted"

        while pages < max_pages:
            pages += 1
            posts, after = await api.list_subreddit_page(
                subreddit,
                sort="new",
                limit=100,
                after=after,
            )
            if not posts:
                stop_reason = "empty"
                break
            page_new = 0
            for p in posts:
                cts = float(p.created_utc)
                if cts <= last_created:
                    stop_reason = "waterline_reached"
                    after = None
                    break
                rec = Submission(
                    id=p.id,
                    title=p.title,
                    selftext=p.selftext,
                    score=p.score,
                    num_comments=p.num_comments,
                    created_utc=cts,
                    subreddit=p.subreddit,
                    author=p.author,
                    url=p.url,
                    permalink=p.permalink,
                )
                if writer is not None:
                    writer.write_record(rec)
                total_new += 1
                page_new += 1
                if cts > max_seen_created:
                    max_seen_created = cts
                    last_id = p.id
            # 更新进度
            _write_progress(progress, {
                "subreddit": subreddit,
                "status": "running",
                "last_seen_created_utc": last_created,
                "pages": pages,
                "new_posts": total_new,
                "after": after,
            })
            if after is None:
                break

    if writer is not None:
        writer.close()

    if total_new > 0 and max_seen_created > last_created:
        _save_waterline(subreddit, max_seen_created, last_id)

    _append_kpi(subreddit=subreddit, new_posts=total_new, pages=pages, stop_reason=stop_reason)
    return {
        "subreddit": subreddit,
        "new_posts": total_new,
        "pages": pages,
        "stop_reason": stop_reason,
        "output": str(output),
        "progress": str(progress),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Incremental crawl via /new with waterline")
    ap.add_argument("--subreddit", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--stream-write", action="store_true")
    args = ap.parse_args()

    try:
        result = asyncio.run(
            crawl_incremental(
                str(args.subreddit).strip(),
                output=Path(str(args.output)),
                max_pages=int(args.max_pages),
                lookback_days=int(args.lookback_days),
                stream_write=bool(args.stream_write),
            )
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
