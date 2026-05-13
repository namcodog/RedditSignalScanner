#!/usr/bin/env python3
from __future__ import annotations

"""
Export entity dictionary (root yaml + folder of yamls) to a flat CSV.

Inputs:
  - backend/config/entity_dictionary.yaml (optional)
  - backend/config/entity_dictionary/*.yml (optional)

Output:
  - backend/reports/local-acceptance/entity-dictionary-export.csv

CSV columns: category, term, source
  - source = 'root' for entity_dictionary.yaml, otherwise the filename stem.
"""

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend/reports/local-acceptance/entity-dictionary-export.csv"


def _load_mapping(path: Path) -> Dict[str, List[str]]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    out: Dict[str, List[str]] = {}
    if isinstance(data, Mapping):
        for cat, items in data.items():
            if isinstance(items, Iterable) and not isinstance(items, (str, bytes)):
                vals = [str(x).strip() for x in items if isinstance(x, (str, int, float))]
                out[str(cat)] = [v for v in vals if v]
    return out


def main() -> int:
    rows: List[Dict[str, str]] = []

    # 1) root dictionary
    root_yaml = ROOT / "backend/config/entity_dictionary.yaml"
    root_map = _load_mapping(root_yaml)
    for cat, items in root_map.items():
        for term in items:
            rows.append({"category": cat, "term": term, "source": "root"})

    # 2) folder yamls
    folder = ROOT / "backend/config/entity_dictionary"
    if folder.exists():
        for yml in sorted(folder.glob("*.yml")):
            mapping = _load_mapping(yml)
            for cat, items in mapping.items():
                for term in items:
                    rows.append({"category": cat, "term": term, "source": yml.stem})

    # de-duplicate
    seen: set[tuple[str, str, str]] = set()
    uniq: List[Dict[str, str]] = []
    for r in rows:
        key = (r["category"].lower(), r["term"].lower(), r["source"].lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "term", "source"])
        w.writeheader()
        for r in uniq:
            w.writerow(r)
    print(f"✅ Exported: {OUT} (rows={len(uniq)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

