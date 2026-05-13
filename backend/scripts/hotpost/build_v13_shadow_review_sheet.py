from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")

from app.services.hotpost.published_card_semantic_refresh import semantic_change_summary
from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v12 import find_v12_density_issues
from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v13 import find_v13_title_issues
from backend.scripts.hotpost import run_v13_published_shadow_refresh as shadow


REVIEW_COLUMNS = [
    "source_plan",
    "row_index",
    "card_id",
    "lane",
    "card_type",
    "source_link",
    "review_status",
    "review_notes",
    "semantic_core_scene",
    "semantic_writing_focus",
    "semantic_risk_bounds",
    "semantic_avoid_claims",
    "original_title",
    "v13_title",
    "edit_title",
    "original_summary_line",
    "v13_summary_line",
    "edit_summary_line",
    "original_audience",
    "v13_audience",
    "edit_audience",
    "original_why_now",
    "v13_why_now",
    "edit_why_now",
]

APPLY_STATUSES = {"", "approved", "edit"}
SKIP_STATUSES = {"reject", "skip"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or import a human review sheet for V13 Hotpost shadow refresh plans.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export V13 shadow plan JSON files into an editable CSV review sheet.")
    export_parser.add_argument("--plan", action="append", type=Path, required=True, help="Shadow plan JSON. Repeatable.")
    export_parser.add_argument("--output", type=Path, required=True, help="Output CSV path.")
    export_parser.add_argument("--dedupe-card-id", action="store_true", help="Keep the last successful row when repeated card_id appears.")

    import_parser = subparsers.add_parser("build-plan", help="Build a human-approved apply plan from an edited review CSV.")
    import_parser.add_argument("--review-sheet", type=Path, required=True, help="Edited review CSV.")
    import_parser.add_argument("--output-plan", type=Path, required=True, help="Output V13 apply plan JSON.")
    import_parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    return parser.parse_args(argv)


def export_review_sheet(plan_paths: list[Path], output_path: Path, *, dedupe_card_id: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    row_by_card_id: dict[str, dict[str, Any]] = {}
    for plan_path in plan_paths:
        plan = shadow._load_plan(plan_path)
        for index, row in enumerate(plan["cards"]):
            if row.get("error") or not isinstance(row.get("refreshed_card"), dict) or not row.get("refreshed_card"):
                continue
            review_row = _review_row(plan_path=plan_path, row_index=index, row=row)
            if dedupe_card_id:
                row_by_card_id[str(review_row["card_id"])] = review_row
            else:
                rows.append(review_row)
    if dedupe_card_id:
        rows = list(row_by_card_id.values())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return {"mode": "export", "rows": len(rows), "output": str(output_path)}


def build_plan_from_review_sheet(review_sheet: Path, output_plan: Path) -> dict[str, Any]:
    review_rows = _read_review_csv(review_sheet)
    source_cache: dict[Path, dict[str, Any]] = {}
    output_rows: list[dict[str, Any]] = []
    skipped = 0
    issues: list[dict[str, Any]] = []

    for review_row in review_rows:
        status = str(review_row.get("review_status") or "").strip().lower()
        if status in SKIP_STATUSES:
            skipped += 1
            continue
        if status not in APPLY_STATUSES:
            raise ValueError(f"unsupported review_status for {review_row.get('card_id')}: {status}")

        source_plan = Path(str(review_row["source_plan"]))
        if source_plan not in source_cache:
            source_cache[source_plan] = shadow._load_plan(source_plan)
        plan_row = source_cache[source_plan]["cards"][int(review_row["row_index"])]
        if str(plan_row.get("card_id")) != str(review_row.get("card_id")):
            raise ValueError(f"review row does not match source plan row: {review_row.get('card_id')}")

        merged_row = _apply_review_edits(plan_row, review_row)
        card = merged_row["refreshed_card"]
        title_issues = find_v13_title_issues(card)
        density_issues = find_v12_density_issues(card)
        if title_issues or density_issues:
            issues.append(
                {
                    "card_id": card.get("card_id"),
                    "title_issues": title_issues,
                    "density_issues": density_issues,
                }
            )
        output_rows.append(merged_row)

    if issues:
        preview = json.dumps(issues[:5], ensure_ascii=False)
        raise ValueError(f"review sheet contains quality issues: {preview}")

    plan = {
        "kind": shadow.PLAN_KIND,
        "plan_version": shadow.PLAN_VERSION,
        "profile_id": shadow.V13_PROFILE_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "selected": len(output_rows),
        "generated": len(output_rows),
        "failed": 0,
        "cards": output_rows,
    }
    output_plan.parent.mkdir(parents=True, exist_ok=True)
    output_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"mode": "build_plan", "selected": len(output_rows), "skipped": skipped, "output_plan": str(output_plan)}


def _review_row(*, plan_path: Path, row_index: int, row: dict[str, Any]) -> dict[str, Any]:
    original = row.get("original_card") if isinstance(row.get("original_card"), dict) else {}
    refreshed = row.get("refreshed_card") if isinstance(row.get("refreshed_card"), dict) else {}
    semantic_brief = row.get("semantic_brief") if isinstance(row.get("semantic_brief"), dict) else {}
    return {
        "source_plan": str(plan_path),
        "row_index": row_index,
        "card_id": row.get("card_id") or refreshed.get("card_id") or "",
        "lane": row.get("lane") or refreshed.get("lane") or "",
        "card_type": row.get("card_type") or refreshed.get("card_type") or "",
        "source_link": original.get("source_link") or refreshed.get("source_link") or "",
        "review_status": "approved",
        "review_notes": "",
        "semantic_core_scene": semantic_brief.get("core_scene") or "",
        "semantic_writing_focus": semantic_brief.get("writing_focus") or "",
        "semantic_risk_bounds": semantic_brief.get("risk_bounds") or "",
        "semantic_avoid_claims": _compact_json(semantic_brief.get("avoid_claims") or []),
        "original_title": original.get("title") or "",
        "v13_title": refreshed.get("title") or "",
        "edit_title": "",
        "original_summary_line": original.get("summary_line") or "",
        "v13_summary_line": refreshed.get("summary_line") or "",
        "edit_summary_line": "",
        "original_audience": original.get("audience") or "",
        "v13_audience": refreshed.get("audience") or "",
        "edit_audience": "",
        "original_why_now": original.get("why_now") or "",
        "v13_why_now": refreshed.get("why_now") or "",
        "edit_why_now": "",
    }


def _compact_json(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _apply_review_edits(plan_row: dict[str, Any], review_row: dict[str, str]) -> dict[str, Any]:
    if plan_row.get("error") or not isinstance(plan_row.get("refreshed_card"), dict) or not plan_row.get("refreshed_card"):
        raise ValueError(f"source plan row is not a successful refreshed card: {plan_row.get('card_id')}")

    refreshed = dict(plan_row["refreshed_card"])
    for sheet_key, card_key in (
        ("edit_title", "title"),
        ("edit_summary_line", "summary_line"),
        ("edit_audience", "audience"),
        ("edit_why_now", "why_now"),
    ):
        value = str(review_row.get(sheet_key) or "").strip()
        if value:
            refreshed[card_key] = value

    merged = dict(plan_row)
    merged["refreshed_card"] = refreshed
    original = plan_row.get("original_card") if isinstance(plan_row.get("original_card"), dict) else {}
    merged["changed"] = semantic_change_summary(original, refreshed)
    merged["v13_title_issues_after"] = find_v13_title_issues(refreshed)
    merged["remaining_density_issues"] = find_v12_density_issues(refreshed)
    merged["error"] = ""
    return merged


def _read_review_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"review sheet does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REVIEW_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"review sheet missing columns: {missing}")
        return [dict(row) for row in reader]


def _print_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(" ".join(f"{key}={value}" for key, value in result.items()))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        if args.command == "export":
            result = export_review_sheet(args.plan, args.output, dedupe_card_id=args.dedupe_card_id)
            _print_result(result, as_json=False)
        elif args.command == "build-plan":
            result = build_plan_from_review_sheet(args.review_sheet, args.output_plan)
            _print_result(result, as_json=args.json)
        else:
            raise ValueError(f"unsupported command: {args.command}")
    except ValueError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
