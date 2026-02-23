"""
Production-safe Step 1 verifier (Operation Crystal Clear)

功能：
- 仅做只读查询，不写库，不调用 LLM（除非 --use-llm 显式开启）。
- 复用 generate_t1_market_report 中的分类器与 _build_facts，输出 market_landscape JSON，
  便于确认平台/品牌/渠道分层是否正确。

用法示例（只读，无 LLM，手动指定品牌补全）：
    python backend/scripts/verify_prod_step1.py \
        --topic "coffee machine" \
        --days 30 \
        --brand-seeds "delonghi,breville,jura"

可选：若允许调用 LLM 补全品牌，则加 --use-llm（会消耗 Token）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory  # noqa: E402
from app.services.blacklist_loader import BlacklistConfig  # noqa: E402
from app.services.t1_stats import build_stats_snapshot  # noqa: E402

# 复用已有工具/分类器
from backend.scripts.generate_t1_market_report import (  # type: ignore  # noqa: E402
    _backfill_brand_mentions,
    _build_facts,
    _fetch_top_brands_from_llm,
    _tokenize_topic,
    _classify_entity,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Step 1 market_landscape (read-only).")
    parser.add_argument("--topic", required=True, help="Topic/market to verify")
    parser.add_argument("--days", type=int, default=30, help="Time window in days")
    parser.add_argument(
        "--brand-seeds",
        type=str,
        default="",
        help="Comma-separated brand seeds to backfill (optional, lowercase/any case)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Call LLM to fetch top brands (will consume tokens). Default off.",
    )
    args = parser.parse_args()

    topic_tokens = _tokenize_topic(args.topic)
    blacklist_config = BlacklistConfig()

    async with SessionFactory() as session:
        # 只读统计快照（无写操作）
        stats = await build_stats_snapshot(session, days=args.days)

        brand_list: List[str] = []
        # 手工种子
        if args.brand_seeds:
            brand_list.extend(
                [b.strip().lower() for b in args.brand_seeds.split(",") if b.strip()]
            )
        # 可选 LLM 补全
        if args.use_llm:
            llm_brands = await _fetch_top_brands_from_llm(args.topic, model="gpt-4o")
            brand_list.extend(llm_brands)

        brand_list = list({b for b in brand_list if b})
        brand_backfill = await _backfill_brand_mentions(session, brand_list) if brand_list else []

        facts_json_str = _build_facts(
            stats,
            clusters=[],
            topic=args.topic,
            topic_tokens=topic_tokens,
            days=args.days,
            selected_communities=None,
            need_distribution=None,
            brand_backfill=brand_backfill,
        )

    facts = json.loads(facts_json_str)
    market = facts.get("market_landscape", {})

    print("=== market_landscape ===")
    print(json.dumps(market, ensure_ascii=False, indent=2))

    # 快速断言：Amazon 应归于 platforms（若存在）
    platforms = {(_classify_entity(p.get("name", "")), p.get("name", "")) for p in market.get("platforms", [])}
    if any(name.lower() == "amazon" for _, name in platforms):
        print("✅ Amazon classified under platforms")
    else:
        print("⚠️ Amazon not present in platforms (check data/time window)")

    # 如果提供了品牌种子，列出命中计数
    if brand_backfill:
        print("=== brand backfill counts ===")
        print(json.dumps(brand_backfill, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
