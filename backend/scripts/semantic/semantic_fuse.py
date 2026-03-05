from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


THEMES = ["what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"]


def read_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def to_map(rows: List[Dict[str, Any]], name_key: str = "name") -> Dict[str, Dict[str, Any]]:
    return {str(r.get(name_key, "")).strip(): r for r in rows if r.get(name_key)}


def load_blacklist(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items: List[str] = []
    if isinstance(data, dict):
        items = list(data.get("blacklist", []))
    elif isinstance(data, list):
        items = list(data)
    return {s.strip().lower() for s in items}


NOISE_SET = {s.lower() for s in [
    "r/strictlycomedancing", "r/aitah", "r/brasil", "r/swiftiemerch",
]}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fuse calibrated semantic and old weighted scores")
    ap.add_argument("--semantic", type=Path, default=Path("backend/data/crossborder_semantic_scored.csv"))
    ap.add_argument("--old", type=Path, default=Path("backend/data/crossborder_candidates_scored.csv"))
    ap.add_argument("--topn", type=int, default=200)
    ap.add_argument("--alpha", type=float, default=0.6, help="semantic weight in fusion")
    ap.add_argument("--min-coverage", type=float, default=0.03)
    ap.add_argument("--min-purity", type=float, default=0.75)
    ap.add_argument("--blacklist", type=Path, default=Path("backend/config/community_blacklist.yaml"))
    args = ap.parse_args()

    sem_rows = read_csv(args.semantic)
    old_rows = read_csv(args.old)
    sem_map = to_map(sem_rows)
    old_map = to_map(old_rows)

    blacklist = load_blacklist(args.blacklist) | NOISE_SET

    out_dir = Path("reports/local-acceptance")
    out_dir.mkdir(parents=True, exist_ok=True)

    for t in THEMES:
        out: List[Dict[str, Any]] = []
        s_key = f"semantic_score_{t}"
        cov_key = f"coverage_{t}"
        pur_key = f"purity_{t}"
        o_key = f"weighted_score_{t}"

        for name, srow in sem_map.items():
            low = name.strip().lower()
            if low in blacklist:
                continue
            try:
                s = float(srow.get(s_key, 0.0) or 0.0)
                cov = float(srow.get(cov_key, 0.0) or 0.0)
                pur = float(srow.get(pur_key, 0.0) or 0.0)
            except Exception:
                s, cov, pur = 0.0, 0.0, 0.0
            if cov < args.min_coverage or pur < args.min_purity:
                continue
            try:
                o = float(old_map.get(name, {}).get(o_key, 0.0) or 0.0)
            except Exception:
                o = 0.0
            fused = round(args.alpha * s + (1.0 - args.alpha) * o, 2)
            out.append(
                {
                    "name": name,
                    f"fused_score_{t}": fused,
                    s_key: round(s, 2),
                    o_key: round(o, 2),
                    cov_key: round(cov, 4),
                    pur_key: round(pur, 4),
                }
            )

        out.sort(key=lambda x: x.get(f"fused_score_{t}", 0.0), reverse=True)
        top = out[: args.topn]
        outp = out_dir / f"crossborder-fused-{t}-top{args.topn}.csv"
        with outp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                    f"fused_score_{t}",
                    s_key,
                    o_key,
                    cov_key,
                    pur_key,
                ],
            )
            writer.writeheader()
            for row in top:
                writer.writerow(row)

        print(f"Top list (fused): {outp}")


if __name__ == "__main__":
    main()

