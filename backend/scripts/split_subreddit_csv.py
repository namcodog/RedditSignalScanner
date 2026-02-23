#!/usr/bin/env python3
from __future__ import annotations

"""
Split a subreddit CSV into N shards and print recommended parallel commands.

Input CSV is expected to contain a column named '社区名称' (fallback: 'subreddit'/'name').
Output shard files retain the same header and are placed next to the input (or --out-dir).

Example:
  python -u backend/scripts/split_subreddit_csv.py \
    --csv ./高价值社区池_基于165社区.csv --shards 3 --since 2018-01 --until 2025-12

This prints two command blocks per shard:
  1) posts (sliced) → full history ingest
  2) comments backfill → full-tree per post
"""

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class ShardInfo:
    path: Path
    index: int
    total: int


def _read_rows(csv_path: Path) -> tuple[List[str], List[dict]]:
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def _detect_name_field(headers: List[str]) -> str:
    for key in ("社区名称", "subreddit", "name"):
        if key in headers:
            return key
    raise ValueError("CSV must contain a '社区名称' (or 'subreddit'/'name') column")


def _write_shards(headers: List[str], rows: List[dict], out_dir: Path, base: str, shards: int) -> List[ShardInfo]:
    chunks: List[List[dict]] = [
        rows[i::shards] for i in range(shards)
    ]  # round-robin split to balance
    out: List[ShardInfo] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, chunk in enumerate(chunks, start=1):
        shard_name = f"{base}_shard{idx}_of_{shards}.csv"
        shard_path = out_dir / shard_name
        with shard_path.open("w", encoding="utf-8", newline="") as wf:
            w = csv.DictWriter(wf, fieldnames=headers)
            w.writeheader()
            for r in chunk:
                w.writerow(r)
        out.append(ShardInfo(path=shard_path, index=idx, total=shards))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Input CSV path (with 列 '社区名称')")
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--out-dir", type=str, default="")
    parser.add_argument("--since", type=str, default="2018-01")
    parser.add_argument("--until", type=str, default=datetime.now().strftime("%Y-%m"))
    parser.add_argument("--per-slice", type=int, default=1000)
    parser.add_argument("--page-size", type=int, default=300)
    parser.add_argument("--commit-interval", type=int, default=10)
    args = parser.parse_args()

    src = Path(args.csv).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else src.parent
    headers, rows = _read_rows(src)
    _ = _detect_name_field(headers)  # validate
    base = src.stem
    shards = max(1, int(args.shards))
    shard_infos = _write_shards(headers, rows, out_dir, base, shards)

    print("\n==> 生成分片:")
    for s in shard_infos:
        print(f"  - {s.path}")

    print("\n==> 建议并行命令（分批执行，避免峰值过高）：\n")
    for s in shard_infos:
        print(f"# === Shard {s.index}/{s.total} ===")
        # Posts (sliced) per shard uses the same master script (reads internal CSV high value list)
        print(
            f"python -u backend/scripts/crawl_posts_high_value.py --mode sliced --since {args.since} --until {args.until} --per-slice {int(args.per_slice)}"
        )
        # Comments backfill for this shard only
        shard_csv = s.path
        print(
            f"make comments-backfill-for-posts CSV='{shard_csv}' DAYS=-1 PAGE_SIZE={int(args.page_size)} COMMIT_INTERVAL={int(args.commit_interval)}\n"
        )


if __name__ == "__main__":
    main()

