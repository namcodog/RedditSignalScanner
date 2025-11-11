#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "local-acceptance"

THEMES: List[Tuple[str, str]] = [
    ("what_to_sell", "跨境选品"),
    ("how_to_sell", "营销/运营"),
    ("where_to_sell", "市场/渠道"),
    ("how_to_source", "供应链/合规/物流"),
]


def _read_top_csv(theme: str) -> List[Dict[str, str]]:
    p = REPORTS / f"crossborder-{theme}-top200.csv"
    rows: List[Dict[str, str]] = []
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def _priority_from_score(score: float) -> Tuple[str, str]:
    if score >= 80:
        return ("关键", "2h")
    if score >= 50:
        return ("关注", "6h")
    return ("观察", "24h")


def main() -> int:
    union: Dict[str, Dict[str, str]] = {}

    for theme, label in THEMES:
        rows = _read_top_csv(theme)
        score_field = f"weighted_score_{theme}"
        for r in rows:
            raw = (r.get("name") or "").strip()
            if not raw:
                continue
            name = raw if raw.startswith("r/") else f"r/{raw}"
            # parse score safely
            try:
                score = float((r.get(score_field) or "0").strip())
            except Exception:
                score = 0.0
            pri, freq = _priority_from_score(score)

            entry = union.get(name) or {
                "community": name,
                "domain_label": label,
                "priority_level": pri,
                "re_crawl_frequency": freq,
                "remarks": "",
            }
            # upgrade priority if this theme yields higher tier
            cur_pri = entry["priority_level"]
            rank = {"关键": 3, "关注": 2, "观察": 1}
            if rank[pri] > rank.get(cur_pri, 0):
                entry["priority_level"] = pri
                entry["re_crawl_frequency"] = freq
            # prefer broader domain_label if already present; otherwise keep first
            union[name] = entry

    # Write output
    out = REPORTS / "high_value_communities_crossborder.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "community",
        "domain_label",
        "priority_level",
        "re_crawl_frequency",
        "remarks",
    ]
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for name in sorted(union.keys()):
            writer.writerow(union[name])
    print(f"✅ Generated: {out}  (rows={len(union)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

