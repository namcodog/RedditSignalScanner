#!/usr/bin/env python3
"""
语料质量校验脚本（Stage 0.1 验收用）

功能：
- 统计每个 JSONL 语料文件的帖子数量、唯一 ID 数、重复数
- 统计 created_utc 的时间范围（最小/最大），估算覆盖天数
- 统计空标题/空正文占比，输出 CSV 报表

用法示例：
    python backend/scripts/validate_corpus.py \
      --corpus-dir backend/data/reddit_corpus \
      --output backend/reports/local-acceptance/corpus_stats.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass
class FileStats:
    path: Path
    subreddit: str
    total: int
    unique_ids: int
    duplicates: int
    min_ts: int | None
    max_ts: int | None
    empty_title_ratio: float
    empty_selftext_ratio: float

    def timespan_days(self) -> float:
        if self.min_ts is None or self.max_ts is None:
            return 0.0
        return max(0.0, (self.max_ts - self.min_ts) / 86400.0)


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def analyze_file(path: Path) -> FileStats:
    ids: set[str] = set()
    total = 0
    dup = 0
    min_ts: int | None = None
    max_ts: int | None = None
    empty_title = 0
    empty_self = 0
    subreddit_name = path.stem

    for row in _iter_jsonl(path):
        total += 1
        sid = str(row.get("id", ""))
        if sid:
            if sid in ids:
                dup += 1
            else:
                ids.add(sid)
        ts = row.get("created_utc")
        try:
            ts_i = int(ts)
            min_ts = ts_i if min_ts is None else min(min_ts, ts_i)
            max_ts = ts_i if max_ts is None else max(max_ts, ts_i)
        except Exception:
            pass
        if not (str(row.get("title", "") or "").strip()):
            empty_title += 1
        if not (str(row.get("selftext", "") or "").strip()):
            empty_self += 1

    empty_title_ratio = (empty_title / total) if total else 0.0
    empty_self_ratio = (empty_self / total) if total else 0.0

    return FileStats(
        path=path,
        subreddit=subreddit_name,
        total=total,
        unique_ids=len(ids),
        duplicates=dup,
        min_ts=min_ts,
        max_ts=max_ts,
        empty_title_ratio=empty_title_ratio,
        empty_selftext_ratio=empty_self_ratio,
    )


def validate_corpus(corpus_dir: str, output_csv: str) -> List[FileStats]:
    d = Path(corpus_dir)
    d.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in d.glob("*.jsonl") if p.is_file()])
    stats: List[FileStats] = [analyze_file(p) for p in files]

    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "subreddit",
            "file",
            "total_posts",
            "unique_ids",
            "duplicates",
            "min_created_utc",
            "max_created_utc",
            "min_created_at",
            "max_created_at",
            "timespan_days",
            "empty_title_ratio",
            "empty_selftext_ratio",
        ])
        for s in stats:
            min_dt = (
                datetime.fromtimestamp(s.min_ts, tz=timezone.utc).isoformat()
                if s.min_ts is not None
                else ""
            )
            max_dt = (
                datetime.fromtimestamp(s.max_ts, tz=timezone.utc).isoformat()
                if s.max_ts is not None
                else ""
            )
            w.writerow([
                s.subreddit,
                str(s.path),
                s.total,
                s.unique_ids,
                s.duplicates,
                s.min_ts or "",
                s.max_ts or "",
                min_dt,
                max_dt,
                f"{s.timespan_days():.1f}",
                f"{s.empty_title_ratio:.3f}",
                f"{s.empty_selftext_ratio:.3f}",
            ])

    # 控制台打印摘要
    for s in stats:
        print(
            json.dumps(
                {
                    "subreddit": s.subreddit,
                    "total": s.total,
                    "unique": s.unique_ids,
                    "dup": s.duplicates,
                    "timespan_days": round(s.timespan_days(), 1),
                    "min": s.min_ts,
                    "max": s.max_ts,
                },
                ensure_ascii=False,
            )
        )

    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate lexicon corpus JSONL files")
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    validate_corpus(args.corpus_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

