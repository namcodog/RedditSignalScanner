from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Any


def read_freeze(path: Path) -> Dict[str, Dict[str, Any]]:
    m: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            m[name] = {
                "priority": (row.get("priority") or "").strip(),
                "themes": (row.get("themes") or "").strip(),
            }
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description="Diff two pool freeze CSV files")
    ap.add_argument(
        "--old",
        type=Path,
        default=Path("backend/reports/local-acceptance/crossborder_pool_freeze.csv"),
    )
    ap.add_argument(
        "--new",
        type=Path,
        default=Path(
            "backend/reports/local-acceptance/crossborder_pool_freeze_semantic_fused.csv"
        ),
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path(
            "backend/reports/local-acceptance/crossborder_pool_diff_semantic_fused.csv"
        ),
    )
    args = ap.parse_args()

    old_map = read_freeze(args.old)
    new_map = read_freeze(args.new)

    old_names = set(old_map.keys())
    new_names = set(new_map.keys())
    all_names = sorted(old_names | new_names)

    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "status",
                "old_priority",
                "new_priority",
                "old_themes",
                "new_themes",
            ],
        )
        writer.writeheader()
        for name in all_names:
            o = old_map.get(name)
            n = new_map.get(name)
            if o and not n:
                writer.writerow(
                    {
                        "name": name,
                        "status": "removed",
                        "old_priority": o.get("priority", ""),
                        "new_priority": "",
                        "old_themes": o.get("themes", ""),
                        "new_themes": "",
                    }
                )
            elif n and not o:
                writer.writerow(
                    {
                        "name": name,
                        "status": "added",
                        "old_priority": "",
                        "new_priority": n.get("priority", ""),
                        "old_themes": "",
                        "new_themes": n.get("themes", ""),
                    }
                )
            else:
                # present in both
                status = "unchanged"
                if (o or {}).get("priority") != (n or {}).get("priority"):
                    status = "priority_changed"
                writer.writerow(
                    {
                        "name": name,
                        "status": status,
                        "old_priority": (o or {}).get("priority", ""),
                        "new_priority": (n or {}).get("priority", ""),
                        "old_themes": (o or {}).get("themes", ""),
                        "new_themes": (n or {}).get("themes", ""),
                    }
                )

    # Print quick summary
    added = len([1 for n in new_names - old_names])
    removed = len([1 for n in old_names - new_names])
    changed = sum(
        1
        for n in (old_names & new_names)
        if old_map[n].get("priority") != new_map[n].get("priority")
    )
    print(
        f"✅ Diff written: {out}\n   added={added}, removed={removed}, priority_changed={changed}, common={len(old_names & new_names)}"
    )


if __name__ == "__main__":
    main()

