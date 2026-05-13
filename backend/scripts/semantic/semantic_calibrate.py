from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any, Dict, List


THEMES = ["what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"]


def read_semantic_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def quantiles(values: List[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    xs = sorted(values)
    n = len(xs)
    def q(p: float) -> float:
        idx = max(0, min(n - 1, int(p * (n - 1))))
        return xs[idx]
    return q(0.5), q(0.95)


def calibrate(scores: List[float]) -> tuple[float, float]:
    q50, q95 = quantiles(scores)
    delta = max(1e-6, q95 - q50)
    return q50, delta


def main() -> None:
    ap = argparse.ArgumentParser(description="Calibrate semantic scores and output TopN lists")
    ap.add_argument("--input", type=Path, default=Path("backend/data/crossborder_semantic_scored.csv"))
    ap.add_argument("--topn", type=int, default=200)
    ap.add_argument("--min-coverage", type=float, default=0.05)
    ap.add_argument("--min-purity", type=float, default=0.80)
    args = ap.parse_args()

    data = read_semantic_csv(args.input)

    # Prepare quantiles per theme
    qinfo: Dict[str, tuple[float, float]] = {}
    for t in THEMES:
        vals: List[float] = []
        for r in data:
            try:
                v = float(r.get(f"semantic_score_{t}", 0.0) or 0.0)
            except Exception:
                v = 0.0
            vals.append(v)
        qinfo[t] = calibrate(vals)

    out_dir = Path("reports/local-acceptance")
    out_dir.mkdir(parents=True, exist_ok=True)

    for t in THEMES:
        base_key = f"semantic_score_{t}"
        cov_key = f"coverage_{t}"
        pur_key = f"purity_{t}"
        q50, delta = qinfo[t]

        enriched: List[Dict[str, Any]] = []
        for r in data:
            try:
                base = float(r.get(base_key, 0.0) or 0.0)
                cov = float(r.get(cov_key, 0.0) or 0.0)
                pur = float(r.get(pur_key, 0.0) or 0.0)
                posts = float(r.get("posts_sampled", 0) or 0)
            except Exception:
                base, cov, pur, posts = 0.0, 0.0, 0.0, 0.0

            # skip if below purity/coverage gate
            if cov < args.min_coverage or pur < args.min_purity:
                continue

            # piecewise linear calibration with conf weighting
            s_norm = (base - q50) / delta
            s_norm = max(0.0, min(1.0, s_norm))
            s_cal = 60.0 + 30.0 * s_norm  # P50->60, P95->90
            conf = max(0.7, min(1.0, math.sqrt(max(1.0, posts) / 10.0)))
            s_final = round(s_cal * conf, 2)

            enriched.append(
                {
                    "name": r.get("name", ""),
                    "posts_sampled": r.get("posts_sampled", "0"),
                    f"semantic_calibrated_{t}": s_final,
                    base_key: round(base, 2),
                    cov_key: round(cov, 4),
                    pur_key: round(pur, 4),
                }
            )

        enriched.sort(key=lambda x: x.get(f"semantic_calibrated_{t}", 0.0), reverse=True)
        top = enriched[: args.topn]
        outp = out_dir / f"crossborder-semantic-calibrated-{t}-top{args.topn}.csv"
        with outp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                    "posts_sampled",
                    f"semantic_calibrated_{t}",
                    base_key,
                    cov_key,
                    pur_key,
                ],
            )
            writer.writeheader()
            for row in top:
                writer.writerow(row)

        print(f"Top list (calibrated): {outp}")


if __name__ == "__main__":
    main()

