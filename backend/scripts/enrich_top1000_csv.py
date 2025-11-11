#!/usr/bin/env python3
from __future__ import annotations

"""
Enrich scraped Top 1000 CSV with domain_label, tags, quality_score,
default_weight, estimated_daily_posts using rule-based mapping.

Inputs:
  - backend/data/top1000_scraped.csv (or custom via --input)
  - backend/config/top1000_enrichment_rules.yml

Outputs:
  - backend/data/top1000_enriched.csv (default)

Usage:
  python backend/scripts/enrich_top1000_csv.py \
    --input backend/data/top1000_scraped.csv \
    --output backend/data/top1000_enriched.csv

Then convert to JSON:
  make top1000-from-csv FILE=backend/data/top1000_enriched.csv OUTPUT=backend/data/top1000_subreddits.json
"""

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore


@dataclass
class Rule:
    name: str
    match: list[str]
    tags: list[str]
    quality_score: float | None
    default_weight: int | None
    estimated_daily_posts: int | None


def load_rules(path: Path) -> tuple[dict[str, Any], list[Rule]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults", {}) or {}
    rules: list[Rule] = []
    for item in payload.get("categories", []) or []:
        rules.append(
            Rule(
                name=str(item.get("name") or ""),
                match=[str(s) for s in (item.get("match") or [])],
                tags=[str(s) for s in (item.get("tags") or [])],
                quality_score=(item.get("quality_score")),
                default_weight=(item.get("default_weight")),
                estimated_daily_posts=(item.get("estimated_daily_posts")),
            )
        )
    return defaults, rules


def normalise_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return n
    return n if n.lower().startswith("r/") else f"r/{n}"


def match_rule(sub_name: str, rules: list[Rule]) -> Rule | None:
    target = sub_name.lower().lstrip("r/")
    for r in rules:
        for pat in r.match:
            if pat.lower() in target:
                return r
    return None


def enrich_row(row: dict[str, Any], defaults: dict[str, Any], rules: list[Rule]) -> dict[str, Any]:
    name = normalise_name(str(row.get("name", "")))
    row["name"] = name
    matched = match_rule(name, rules)

    # domain_label
    if (not row.get("domain_label")) and matched:
        row["domain_label"] = matched.name

    # tags: merge existing with rule tags and tokens from name
    tags: list[str] = []
    raw = str(row.get("tags", ""))
    if raw:
        tags.extend([t.strip() for t in raw.replace("|", ",").split(",") if t.strip()])
    if matched and matched.tags:
        tags.extend(matched.tags)
    # tokens from name
    tokens = re.split(r"[_/]+", name.lstrip("r/"))
    for t in tokens:
        if t and t.lower() not in {x.lower() for x in tags}:
            tags.append(t)
    row["tags"] = "|".join(tags)

    # quality_score/default_weight/estimated_daily_posts: if matched, prefer rule values; else keep existing
    def _num(val: Any, t=float, fallback=None):
        try:
            return t(val)
        except Exception:
            return fallback

    if matched and matched.quality_score is not None:
        row["quality_score"] = matched.quality_score
    else:
        current_q = _num(row.get("quality_score"), float, None)
        if current_q is None:
            row["quality_score"] = defaults.get("quality_score", 0.6)

    if matched and matched.default_weight is not None:
        row["default_weight"] = matched.default_weight
    else:
        current_w = _num(row.get("default_weight"), int, None)
        if current_w is None:
            row["default_weight"] = int(defaults.get("default_weight", 60))

    if matched and matched.estimated_daily_posts is not None:
        row["estimated_daily_posts"] = matched.estimated_daily_posts
    else:
        current_e = _num(row.get("estimated_daily_posts"), int, None)
        if current_e is None or current_e == 0:
            row["estimated_daily_posts"] = int(defaults.get("estimated_daily_posts", 30))

    return row


def run(input_path: Path, output_path: Path, rules_path: Path) -> int:
    defaults, rules = load_rules(rules_path)
    rows: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(enrich_row(row, defaults, rules))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "name",
                "domain_label",
                "tags",
                "quality_score",
                "default_weight",
                "estimated_daily_posts",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"✅ Enriched {len(rows)} rows -> {output_path}")
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description="Enrich Top1000 CSV with rule-based fields")
    p.add_argument("--input", default=str(root / "backend/data/top1000_scraped.csv"))
    p.add_argument("--output", default=str(root / "backend/data/top1000_enriched.csv"))
    p.add_argument("--rules", default=str(root / "backend/config/top1000_enrichment_rules.yml"))
    args = p.parse_args()
    return run(Path(args.input), Path(args.output), Path(args.rules))


if __name__ == "__main__":
    raise SystemExit(main())
