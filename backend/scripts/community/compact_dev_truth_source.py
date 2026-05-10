from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from app.db import SessionFactory
from app.services.community.dev_truth_source_compaction_service import (
    compact_dev_truth_source,
)


async def _main(dry_run: bool) -> Path:
    async with SessionFactory() as session:
        result = await compact_dev_truth_source(
            session,
            database_url=os.environ["DATABASE_URL"],
            dry_run=dry_run,
        )
    out_dir = Path("backend/reports/local-acceptance")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"dev_truth_compaction_{int(time.time())}.json"
    out_path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = asyncio.run(_main(dry_run=not args.write))
    print(path)
