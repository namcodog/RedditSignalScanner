#!/usr/bin/env python3
from __future__ import annotations

"""Spec 011 Stage 3 – Weekly calibration workflow helper."""

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


DEFAULT_CANDIDATES = Path("backend/reports/local-acceptance/crossborder_candidates.csv")
DEFAULT_SAMPLES = Path("backend/reports/local-acceptance/review_samples.csv")
DEFAULT_UI = Path("backend/reports/local-acceptance/review_ui.html")
DEFAULT_NOTES = Path("backend/reports/local-acceptance/review_notes.md")
DEFAULT_EXCLUDE = Path("backend/config/semantic_sets/exclude_reasons.csv")
DEFAULT_CHANGELOG = Path("backend/config/semantic_sets/CHANGELOG.md")


@dataclass
class CandidateRecord:
    canonical: str
    category: str
    layer: str
    freq: int
    score: float


@dataclass
class ReviewDecision:
    canonical: str
    category: str
    layer: str
    freq: int
    score: float
    risk_score: float
    task_id: str
    risk_bucket: str = "high"
    decision: str = "pending"
    target: str = ""
    notes: str = ""
    status: str = "pending"
    source: str = ""


def load_candidates(path: Path) -> List[CandidateRecord]:
    records: List[CandidateRecord] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = (row.get("canonical") or row.get("term") or row.get("candidate") or "").strip()
            if not canonical:
                continue
            category = (row.get("category") or row.get("theme") or "features").strip()
            layer = (row.get("layer") or row.get("layers") or "").strip()
            try:
                freq = int(float(row.get("freq") or row.get("count") or 0))
            except ValueError:
                freq = 0
            try:
                score = float(row.get("score") or row.get("weight") or 0.0)
            except ValueError:
                score = 0.0
            records.append(CandidateRecord(canonical, category, layer, freq, score))
    return records


def _normalise(values: Sequence[float]) -> Dict[float, float]:
    if not values:
        return {}
    v_min = min(values)
    v_max = max(values)
    span = (v_max - v_min) or 1.0
    return {val: (val - v_min) / span for val in values}


def _risk_bucket(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def select_review_samples(
    candidates: Sequence[CandidateRecord],
    *,
    task_id: str,
    sample_rate: float,
    stratify: bool,
) -> List[ReviewDecision]:
    if not candidates:
        return []
    scores_norm = _normalise([c.score for c in candidates])
    max_freq = max(c.freq for c in candidates) or 1
    enriched: List[ReviewDecision] = []
    for cand in candidates:
        score_norm = scores_norm.get(cand.score, 0.0)
        freq_norm = cand.freq / max_freq
        risk = (1 - score_norm) * 0.7 + freq_norm * 0.3
        enriched.append(
            ReviewDecision(
                canonical=cand.canonical,
                category=cand.category or "features",
                layer=cand.layer or "",
                freq=cand.freq,
                score=cand.score,
                risk_score=risk,
                risk_bucket=_risk_bucket(risk),
                task_id=task_id,
            )
        )

    def _pick(group: Sequence[ReviewDecision], count: int) -> List[ReviewDecision]:
        return sorted(group, key=lambda r: r.risk_score, reverse=True)[: max(1, count)]

    if stratify:
        grouped: Dict[str, List[ReviewDecision]] = defaultdict(list)
        for row in enriched:
            grouped[row.layer].append(row)
        selected: List[ReviewDecision] = []
        for layer, rows in grouped.items():
            take = max(1, round(len(rows) * sample_rate))
            selected.extend(_pick(rows, take))
    else:
        total = max(1, round(len(enriched) * sample_rate))
        selected = _pick(enriched, total)
    return selected


def write_samples_csv(rows: Sequence[ReviewDecision], path: Path, *, source: Path, sample_rate: float) -> None:
    headers = [
        "task_id",
        "canonical",
        "category",
        "layer",
        "freq",
        "score",
        "risk_score",
        "risk_bucket",
        "decision",
        "target",
        "notes",
        "status",
        "source_file",
        "sample_rate",
        "sampled_at",
    ]
    sampled_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "task_id": row.task_id,
                    "canonical": row.canonical,
                    "category": row.category,
                    "layer": row.layer,
                    "freq": row.freq,
                    "score": f"{row.score:.4f}",
                    "risk_score": f"{row.risk_score:.4f}",
                    "risk_bucket": row.risk_bucket,
                    "decision": row.decision,
                    "target": row.target,
                    "notes": row.notes,
                    "status": row.status,
                    "source_file": source.as_posix(),
                    "sample_rate": sample_rate,
                    "sampled_at": sampled_at,
                }
            )


def read_review_samples(path: Path) -> List[ReviewDecision]:
    rows: List[ReviewDecision] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row.get("canonical", "").strip()
            if not canonical:
                continue
            try:
                score = float(row.get("score") or 0.0)
            except ValueError:
                score = 0.0
            try:
                freq = int(float(row.get("freq") or 0))
            except ValueError:
                freq = 0
            try:
                risk = float(row.get("risk_score") or 0.0)
            except ValueError:
                risk = 0.0
            rows.append(
                ReviewDecision(
                    canonical=canonical,
                    category=(row.get("category") or "features").strip(),
                    layer=(row.get("layer") or "").strip(),
                    freq=freq,
                    score=score,
                    risk_score=risk,
                    risk_bucket=row.get("risk_bucket", "high"),
                    task_id=row.get("task_id", "calibration"),
                    decision=(row.get("decision") or "").strip().lower(),
                    target=(row.get("target") or "").strip(),
                    notes=row.get("notes", ""),
                    status=(row.get("status") or "pending").strip(),
                    source=row.get("source_file", ""),
                )
            )
    return rows


def generate_review_ui(rows: Sequence[ReviewDecision], output_path: Path) -> None:
    rows_sorted = sorted(rows, key=lambda r: (r.layer, -r.risk_score))
    totals = defaultdict(int)
    for row in rows_sorted:
        totals[row.decision or "pending"] += 1
    summary_lines = ["<h1>Weekly Calibration Review</h1>", "<ul>"]
    for decision, count in sorted(totals.items()):
        summary_lines.append(f"  <li>{decision or 'pending'}: {count}</li>")
    summary_lines.append("</ul>")

    table_rows = [
        "<table>",
        "<thead><tr><th>Layer</th><th>Category</th><th>Term</th><th>Freq</th><th>Score</th><th>Risk</th><th>Decision</th><th>Target</th><th>Notes</th></tr></thead>",
        "<tbody>",
    ]
    for row in rows_sorted:
        table_rows.append(
            "  <tr>"
            f"<td>{row.layer}</td>"
            f"<td>{row.category}</td>"
            f"<td>{row.canonical}</td>"
            f"<td>{row.freq}</td>"
            f"<td>{row.score:.2f}</td>"
            f"<td>{row.risk_bucket} ({row.risk_score:.2f})</td>"
            f"<td>{row.decision or 'pending'}</td>"
            f"<td>{row.target}</td>"
            f"<td>{row.notes}</td>"
            "</tr>"
        )
    table_rows.append("</tbody></table>")

    output_path.write_text("\n".join(summary_lines + table_rows), encoding="utf-8")


def _ensure_layer_category(data: dict, layer: str, category: str) -> List[dict]:
    layers = data.setdefault("layers", {})
    layer_block = layers.setdefault(layer, {})
    if not isinstance(layer_block, dict):
        raise ValueError(f"Layer {layer} must be a dict in lexicon")
    bucket = layer_block.setdefault(category, [])
    if not isinstance(bucket, list):
        raise ValueError(f"Category {category} must be a list in lexicon")
    return bucket


def _default_entry(row: ReviewDecision) -> dict:
    precision = "phrase" if " " in row.canonical else "exact"
    polarity = "negative" if row.category == "pain_points" else "neutral"
    weight = max(row.score, float(row.freq)) or 1.0
    return {
        "canonical": row.canonical,
        "aliases": [],
        "precision_tag": precision,
        "weight": weight,
        "polarity": polarity,
    }


def _append_exclude(term: str, layer: str, reason: str, exclude_path: Path) -> None:
    if not exclude_path.exists():
        exclude_path.write_text("term,reason,example_subreddit,added_date,layer\n", encoding="utf-8")
    added_date = datetime.utcnow().strftime("%Y-%m-%d")
    with exclude_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([term, reason, "", added_date, layer])


def append_review_notes(notes_path: Path, task_id: str, summary: Dict[str, int], rows: Sequence[ReviewDecision]) -> None:
    lines = []
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    lines.append(f"## Calibration {task_id} ({timestamp})\n")
    lines.append("Action summary:")
    for action, count in sorted(summary.items()):
        lines.append(f"- {action}: {count}")
    lines.append("")
    lines.append("Reviewed terms:")
    for row in rows:
        if not row.decision:
            continue
        lines.append(
            f"- {row.canonical} ({row.layer}/{row.category}) → {row.decision} {row.target or ''} {row.notes or ''}".strip()
        )
    lines.append("\n")
    with notes_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def append_changelog(changelog_path: Path, task_id: str, summary: Dict[str, int]) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [f"## [Calibration {task_id}] - {timestamp}"]
    for action, count in sorted(summary.items()):
        lines.append(f"- {action}: {count}")
    lines.append("")
    with changelog_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def apply_calibration_changes(
    lexicon: dict,
    decisions: Sequence[ReviewDecision],
    *,
    exclude_path: Path | None,
    changelog_path: Path | None,
    notes_path: Path | None,
    task_id: str,
) -> Dict[str, int]:
    recognised = {"merge", "add", "delete", "blacklist"}
    summary: Dict[str, int] = defaultdict(int)
    applied_rows: List[ReviewDecision] = []

    for row in decisions:
        action = (row.decision or "").strip().lower()
        if action not in recognised:
            continue
        bucket = _ensure_layer_category(lexicon, row.layer or "L2", row.category or "features")
        if action == "merge":
            target = (row.target or "").strip()
            if not target:
                continue
            entry = _find_entry(lexicon, target)
            if not entry:
                continue
            aliases = entry.setdefault("aliases", [])
            alias_low = row.canonical.lower()
            if alias_low == entry.get("canonical", "").lower():
                continue
            if any(str(a).lower() == alias_low for a in aliases):
                continue
            aliases.append(row.canonical)
        elif action == "add":
            if _find_entry(lexicon, row.canonical):
                continue
            bucket.append(_default_entry(row))
        elif action == "delete":
            before = len(bucket)
            bucket[:] = [item for item in bucket if item.get("canonical") != row.canonical]
            if len(bucket) == before:
                continue
        elif action == "blacklist":
            if exclude_path:
                _append_exclude(row.canonical, row.layer, row.notes or f"calibration {task_id}", exclude_path)
        summary[action] += 1
        applied_rows.append(row)

    if summary and notes_path:
        append_review_notes(notes_path, task_id, summary, applied_rows)
    if summary and changelog_path:
        append_changelog(changelog_path, task_id, summary)
    return summary


def _find_entry(lexicon: dict, canonical: str) -> dict | None:
    for layer_block in lexicon.get("layers", {}).values():
        if not isinstance(layer_block, dict):
            continue
        for arr in layer_block.values():
            if not isinstance(arr, list):
                continue
            for item in arr:
                if item.get("canonical") == canonical:
                    return item
    return None


def _auto_task_id() -> str:
    return f"calib-{datetime.utcnow().strftime('%Y%m%d')}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Weekly calibration helper")
    parser.add_argument("--task-id", default=_auto_task_id())
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--sample-rate", type=float, default=0.1)
    parser.add_argument("--stratify-by-layer", action="store_true")
    parser.add_argument("--output", type=Path, help="Output file (CSV/HTML/new lexicon)")
    parser.add_argument("--generate-review-ui", action="store_true")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--apply", type=Path, help="Annotated sample CSV to apply")
    parser.add_argument("--lexicon", type=Path, help="Lexicon file for apply step")
    parser.add_argument("--review-notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--exclude-file", type=Path, default=DEFAULT_EXCLUDE)
    parser.add_argument("--changelog", type=Path, default=DEFAULT_CHANGELOG)
    parser.add_argument("--update-changelog", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if args.generate_review_ui:
        if not args.samples or not args.output:
            raise SystemExit("--samples and --output are required for --generate-review-ui")
        rows = read_review_samples(args.samples)
        generate_review_ui(rows, args.output)
        print(f"Review UI written to {args.output}")
        return

    if args.apply:
        if not args.lexicon or not args.output:
            raise SystemExit("--lexicon and --output are required for --apply")
        rows = read_review_samples(args.apply)
        data = json.loads(args.lexicon.read_text(encoding="utf-8"))
        summary = apply_calibration_changes(
            data,
            rows,
            exclude_path=args.exclude_file,
            changelog_path=args.changelog if args.update_changelog else None,
            notes_path=args.review_notes,
            task_id=args.task_id or rows[0].task_id,
        )
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Applied calibration ({sum(summary.values())} actions) → {args.output}")
        return

    # default: sample extraction
    if not args.output:
        raise SystemExit("--output is required when sampling")
    candidates = load_candidates(args.candidates)
    rows = select_review_samples(
        candidates,
        task_id=args.task_id,
        sample_rate=max(0.01, float(args.sample_rate)),
        stratify=args.stratify_by_layer,
    )
    write_samples_csv(rows, args.output, source=args.candidates, sample_rate=args.sample_rate)
    print(f"Sampled {len(rows)} rows → {args.output}")


if __name__ == "__main__":
    main()
