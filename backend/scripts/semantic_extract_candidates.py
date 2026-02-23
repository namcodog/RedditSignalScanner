from __future__ import annotations

"""
Extract candidate brand terms from posts_hot using CandidateExtractor.

Usage:
  python backend/scripts/semantic_extract_candidates.py \
    --lookback-days 30 --min-frequency 5 \
    --output backend/reports/semantic-candidates/candidates.csv

Columns:
  canonical | aliases | confidence | frequency | evidence_post_ids | suggested_layer | first_seen
  - aliases: pipe-separated (e.g., "AMZ|亚马逊")
  - evidence_post_ids: JSON array string (e.g., "[123,456]")
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List

from app.db.session import SessionFactory
from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.semantic.candidate_extractor import CandidateExtractor, CandidateTerm


def write_csv_spec(cands: List[CandidateTerm], out: Path) -> None:
    import csv

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "canonical",
                "aliases",
                "confidence",
                "frequency",
                "evidence_post_ids",
                "suggested_layer",
                "first_seen",
            ],
        )
        writer.writeheader()
        # sort by confidence desc, frequency desc
        cands_sorted = sorted(cands, key=lambda x: (x.confidence, x.frequency), reverse=True)
        for c in cands_sorted:
            writer.writerow(
                {
                    "canonical": c.canonical,
                    "aliases": "|".join(c.aliases),
                    "confidence": f"{c.confidence:.3f}",
                    "frequency": c.frequency,
                    "evidence_post_ids": json.dumps(c.evidence_post_ids, ensure_ascii=False),
                    "suggested_layer": c.suggested_layer,
                    "first_seen": c.first_seen,
                }
            )


async def run() -> Path:
    ap = argparse.ArgumentParser(description="Extract candidate brand terms from posts_hot")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/unified_lexicon.yml"))
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--min-frequency", type=int, default=5)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path(f"backend/reports/semantic-candidates/candidates_{datetime.now():%Y%m%d}.csv"),
    )
    args = ap.parse_args()

    ulex = UnifiedLexicon(args.lexicon)
    ext = CandidateExtractor(lexicon=ulex, min_frequency=int(args.min_frequency))

    async with SessionFactory() as session:
        cands = await ext.extract_from_db(session, lookback_days=int(args.lookback_days), limit=2000)
    write_csv_spec(cands, args.output)
    print(f"Extracted {len(cands)} candidates, written to {args.output}")
    return args.output


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
