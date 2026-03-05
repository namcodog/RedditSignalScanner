#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml


def load_folder(folder: Path) -> dict[str, dict[str, int]]:
    """Return per-file and per-category counts."""
    result: dict[str, dict[str, int]] = {}
    if not folder.exists() or not folder.is_dir():
        return result
    for yml in sorted(folder.glob("*.yml")):
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, Mapping):
            continue
        counts: dict[str, int] = {}
        for cat, items in data.items():
            if isinstance(items, list):
                counts[str(cat)] = sum(1 for it in items if isinstance(it, str) and it.strip())
        result[yml.name] = counts
    return result


def main() -> int:
    folder = Path("backend/config/entity_dictionary")
    summary = load_folder(folder)
    total_by_cat: dict[str, int] = {}
    for counts in summary.values():
        for cat, n in counts.items():
            total_by_cat[cat] = total_by_cat.get(cat, 0) + n

    report = {
        "folder": str(folder),
        "files": summary,
        "total_by_category": total_by_cat,
        "generated_at": datetime.now().isoformat(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    outdir = Path("reports/local-acceptance")
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    (outdir / f"entities-dictionary-check-{ts}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

