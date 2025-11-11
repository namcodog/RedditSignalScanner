#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            theme = (r.get("theme") or "").strip()
            ttype = (r.get("type") or "").strip().lower()
            term = (r.get("term") or "").strip()
            if not theme or not ttype or not term:
                continue
            rows.append({"theme": theme, "type": ttype, "term": term})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Import entity vocabulary CSV into YAML files per theme")
    ap.add_argument("--input", required=True, help="CSV file path: theme,type,term")
    ap.add_argument("--outdir", default="backend/config/entity_dictionary", help="Output directory for YAML files")
    ap.add_argument("--stopwords", default="backend/config/entity_stopwords.yaml", help="Output YAML for stopwords (by theme)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.outdir)
    stop_out = Path(args.stopwords)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_csv(in_path)
    by_theme: Dict[str, Dict[str, set[str]]] = defaultdict(lambda: {"brands": set(), "features": set(), "pain_points": set()})
    stopwords: Dict[str, set[str]] = defaultdict(set)

    for r in rows:
        theme = r["theme"].strip()
        ttype = r["type"].strip().lower()
        term = r["term"].strip()
        if not theme or not term:
            continue
        # normalise type keys
        if ttype in {"brand", "brands"}:
            by_theme[theme]["brands"].add(term)
        elif ttype in {"feature", "features"}:
            by_theme[theme]["features"].add(term)
        elif ttype in {"pain_point", "pain_points"}:
            by_theme[theme]["pain_points"].add(term)
        elif ttype in {"stopword", "stopwords"}:
            stopwords[theme].add(term)
        else:
            # ignore unknown types; could log
            continue

    # Write per-theme YAML files (only brands/features/pain_points)
    for theme, buckets in by_theme.items():
        data = {
            "brands": sorted(buckets["brands"]),
            "features": sorted(buckets["features"]),
            "pain_points": sorted(buckets["pain_points"]),
        }
        out_path = out_dir / f"{theme}.yml"
        out_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=True), encoding="utf-8")

    # Write stopwords to a separate YAML so matching pipeline won't treat them as entities
    stop_data = {theme: sorted(words) for theme, words in stopwords.items()}
    stop_out.parent.mkdir(parents=True, exist_ok=True)
    stop_out.write_text(yaml.safe_dump(stop_data, allow_unicode=True, sort_keys=True), encoding="utf-8")

    print(f"✅ Imported {len(rows)} rows into {out_dir}, stopwords -> {stop_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

