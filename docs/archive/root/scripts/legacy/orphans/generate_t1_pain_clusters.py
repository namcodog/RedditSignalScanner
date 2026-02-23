#!/usr/bin/env python3
"""生成 T1 痛点聚类快照（reports/local-acceptance/t1-pain-clusters.json）。"""
import asyncio
import json
from pathlib import Path

from app.db.session import SessionFactory
from app.services.t1_clustering import build_pain_clusters


async def main() -> None:
    async with SessionFactory() as session:
        clusters = await build_pain_clusters(session)
    output_path = Path("reports/local-acceptance/t1-pain-clusters.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([c.to_dict() for c in clusters], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Pain clusters written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
