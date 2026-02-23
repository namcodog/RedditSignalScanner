#!/usr/bin/env python3
"""
JSONL 入库：脚本只负责“下单”，不再直接写库（收口版）。

口径：
- 写库只能走 Celery Worker（统一执行器）
- 离线入库也必须更新 community_cache 的 waterline（否则巡航会当没发生）
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

from celery.result import AsyncResult

# Ensure `import app.*` works when invoked from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks.ingest_task import ingest_jsonl_backfill

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def _detect_window(path: Path) -> Tuple[str, str]:
    """从 JSONL 里粗略推断时间窗（用于 backfill plan 合同）。"""
    min_dt: datetime | None = None
    max_dt: datetime | None = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            created_utc = data.get("created_utc")
            if created_utc is None:
                continue
            try:
                dt = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            except Exception:
                continue
            if min_dt is None or dt < min_dt:
                min_dt = dt
            if max_dt is None or dt > max_dt:
                max_dt = dt

    if min_dt is None or max_dt is None:
        raise ValueError("无法从 JSONL 解析出 created_utc 时间窗")
    # 半开区间：[since, until)
    return min_dt.isoformat(), (max_dt + timedelta(seconds=1)).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--community", required=True)
    parser.add_argument("--update-watermark", action="store_true")
    parser.add_argument("--since", type=str, default=None, help="ISO8601 (可选，不传则自动探测)")
    parser.add_argument("--until", type=str, default=None, help="ISO8601 (可选，不传则自动探测)")
    parser.add_argument("--crawl-run-id", type=str, default=None, help="可选：指定父级 run_id 方便对账")
    args = parser.parse_args()

    since = args.since
    until = args.until
    if not since or not until:
        since, until = _detect_window(args.file)

    result: AsyncResult = ingest_jsonl_backfill.delay(
        file_path=str(args.file),
        community=str(args.community),
        since=since,
        until=until,
        update_watermark=bool(args.update_watermark),
        crawl_run_id=args.crawl_run_id,
        reason="offline_ingest",
    )
    print(f"[INFO] 已派发任务: {result.id}")
    response = result.get(timeout=None)
    print("[RESULT]", response)

if __name__ == "__main__":
    main()
