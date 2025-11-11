#!/usr/bin/env python3
from __future__ import annotations

"""
Semantic metrics acceptance gate (Spec 011).

Reads metrics snapshot produced by calculate_metrics.py and asserts thresholds.
On failure, prints a concise reason list and exits with non-zero code.

Thresholds are loaded from a YAML file by default:
  backend/config/quality_gates/semantic_thresholds.yml

Environment overrides:
  SEMANTIC_THRESHOLDS_YML: path to thresholds YAML
  SEMANTIC_METRICS_JSON:   path to metrics JSON (default reports/local-acceptance/metrics/metrics.json)
  SEMANTIC_ENTITY_CSV:     path to entity dict CSV (default backend/config/entity_dictionary/crossborder_v2.csv)
"""

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Thresholds:
    overall_coverage_min: float
    brands_coverage_min: float
    features_coverage_min: float | None
    pain_points_coverage_min: float
    layer_coverage_min: Dict[str, float]
    top10_unique_share_min: float
    top10_unique_share_max: float
    entity_dict_min_terms: int


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover - defensive
        raise SystemExit(f"YAML module not available: {e}")
    if not path.exists():
        raise SystemExit(f"Threshold file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_thresholds(yaml_path: Path) -> Thresholds:
    data = _load_yaml(yaml_path)
    layer_min = {
        "L1": float((data.get("layer_coverage_min", {}) or {}).get("L1", 0.85)),
        "L2": float((data.get("layer_coverage_min", {}) or {}).get("L2", 0.80)),
        "L3": float((data.get("layer_coverage_min", {}) or {}).get("L3", 0.75)),
        "L4": float((data.get("layer_coverage_min", {}) or {}).get("L4", 0.70)),
    }
    return Thresholds(
        overall_coverage_min=float(data.get("overall_coverage_min", 0.70)),
        brands_coverage_min=float(data.get("brands_coverage_min", 0.60)),
        features_coverage_min=float(data.get("features_coverage_min", 0.0)) if data.get("features_coverage_min") is not None else None,
        pain_points_coverage_min=float(data.get("pain_points_coverage_min", 0.50)),
        layer_coverage_min=layer_min,
        top10_unique_share_min=float(data.get("top10_unique_share_min", 0.60)),
        top10_unique_share_max=float(data.get("top10_unique_share_max", 0.90)),
        entity_dict_min_terms=int(data.get("entity_dict_min_terms", 100)),
    )


def _load_metrics(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Metrics JSON not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"Invalid metrics JSON: {e}")


def _count_entity_terms(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if (row.get("canonical") or "").strip():
                    count += 1
            return count
    except Exception:
        return 0


def _get_layer_coverage(metrics: Dict[str, Any], layer: str) -> Optional[float]:
    for entry in metrics.get("layer_coverage", []) or []:
        if str(entry.get("layer")) == layer:
            try:
                return float(entry.get("coverage"))
            except Exception:
                return None
    return None


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    phat = successes / total
    denom = 1.0 + (z * z) / total
    centre = phat + (z * z) / (2 * total)
    margin = z * ((phat * (1 - phat) + (z * z) / (4 * total)) / total) ** 0.5
    low = max(0.0, (centre - margin) / denom)
    high = min(1.0, (centre + margin) / denom)
    return (low, high)


def evaluate_gate(metrics: Dict[str, Any], thresholds: Thresholds, entity_terms: int, *, use_ci: bool = False, z: float = 1.96, tolerance: float = 0.0) -> List[str]:
    """Return list of reasons if gate fails; empty list means pass."""
    reasons: List[str] = []

    ent = metrics.get("entity_coverage", {}) or {}
    overall = float(ent.get("overall", 0.0) or 0.0)
    brands = float(ent.get("brands", 0.0) or 0.0)
    pains = float(ent.get("pain_points", 0.0) or 0.0)
    top10 = float(ent.get("top10_unique_share", 0.0) or 0.0)

    if overall < thresholds.overall_coverage_min:
        reasons.append(f"overall_coverage<{thresholds.overall_coverage_min}")
    if brands < thresholds.brands_coverage_min:
        reasons.append(f"brands<{thresholds.brands_coverage_min}")
    if pains < thresholds.pain_points_coverage_min:
        reasons.append(f"pain_points<{thresholds.pain_points_coverage_min}")
    # Optional features coverage gate (only if configured > 0)
    try:
        fmin = thresholds.features_coverage_min
        if fmin is not None and fmin > 0:
            feats = float(ent.get("features", 0.0) or 0.0)
            if feats < fmin:
                reasons.append(f"features<{fmin}")
    except Exception:
        pass
    if not (thresholds.top10_unique_share_min <= top10 <= thresholds.top10_unique_share_max):
        reasons.append(
            f"top10_unique_share∉[{thresholds.top10_unique_share_min},{thresholds.top10_unique_share_max}]"
        )

    for layer, minv in thresholds.layer_coverage_min.items():
        cov = _get_layer_coverage(metrics, layer)
        if cov is None or cov < minv:
            reasons.append(f"{layer}<{minv}")

    if entity_terms < thresholds.entity_dict_min_terms:
        reasons.append(f"entity_terms<{thresholds.entity_dict_min_terms}")

    # Optional CI-based checks (Wilson interval)
    if use_ci:
        try:
            counts = metrics.get("entity_coverage", {})
            total = int(counts.get("total_posts", 0) or 0)
            matched = int(counts.get("matched_posts", 0) or 0)
            top_hits = int(counts.get("top10_unique_hits", 0) or 0)
            low_overall, _ = _wilson_interval(matched, total, z)
            # Require CI lower bound above threshold - tolerance
            if low_overall + tolerance < thresholds.overall_coverage_min:
                reasons.append("overall_coverage_CI_low<threshold")
            # For top10 share, require CI upper bound below max + tolerance
            # Estimate CI on top10_unique_share using matched as denominator
            _, high_top = _wilson_interval(top_hits, max(1, matched), z)
            if high_top - tolerance > thresholds.top10_unique_share_max:
                reasons.append("top10_share_CI_high>max")
        except Exception:
            # If CI computation fails, fall back to point estimates only
            pass

    return reasons


def main() -> int:
    ap = argparse.ArgumentParser(description="Semantic acceptance gate")
    ap.add_argument("--metrics", type=Path, default=Path(os.getenv("SEMANTIC_METRICS_JSON", "backend/reports/local-acceptance/metrics/metrics.json")))
    ap.add_argument("--thresholds", type=Path, default=Path(os.getenv("SEMANTIC_THRESHOLDS_YML", "backend/config/quality_gates/semantic_thresholds.yml")))
    ap.add_argument("--entity-csv", type=Path, default=Path(os.getenv("SEMANTIC_ENTITY_CSV", "backend/config/entity_dictionary/crossborder_v2.csv")))
    ap.add_argument("--use-ci", action="store_true")
    ap.add_argument("--z", type=float, default=1.96)
    ap.add_argument("--tolerance", type=float, default=0.0)
    args = ap.parse_args()

    thresholds = _load_thresholds(args.thresholds)
    metrics = _load_metrics(args.metrics)
    entity_terms = _count_entity_terms(args.entity_csv)

    reasons = evaluate_gate(metrics, thresholds, entity_terms, use_ci=args.use_ci or os.getenv("SEMANTIC_GATE_CI", "0").lower() in {"1","true","yes"}, z=float(args.z), tolerance=float(args.tolerance))
    if reasons:
        print(json.dumps({"status": "fail", "reasons": reasons}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
