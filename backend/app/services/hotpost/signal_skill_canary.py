from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_canary_cases(
    *,
    cases: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    target_packs: list[tuple[str, str]],
    limit_per_pack: int = 3,
) -> list[dict[str, Any]]:
    case_map = {case["eval_case_id"]: case for case in cases}
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scope_id, pack_id in target_packs:
        count = 0
        for prediction in predictions:
            if prediction["overall_pass"]:
                continue
            case = case_map[prediction["eval_case_id"]]
            bundle = case["input_bundle"]
            if case["eval_case_id"] in seen:
                continue
            if case["sample_origin"] != "candidate_generated":
                continue
            if bundle["source_scope_id"] != scope_id or (bundle.get("topic_pack_id") or "unknown") != pack_id:
                continue
            picked.append(case)
            seen.add(case["eval_case_id"])
            count += 1
            if count >= limit_per_pack:
                break
    return picked


def build_canary_report(
    *,
    variant_id: str,
    baseline_predictions: list[dict[str, Any]],
    canary_predictions: list[dict[str, Any]],
    baseline_outputs: list[dict[str, Any]],
    canary_outputs: list[dict[str, Any]],
) -> str:
    baseline_map = {row["eval_case_id"]: row for row in baseline_predictions}
    canary_map = {row["eval_case_id"]: row for row in canary_predictions}
    base_output_map = {row["eval_case_id"]: row for row in baseline_outputs}
    canary_output_map = {row["eval_case_id"]: row for row in canary_outputs}
    rows = [
        "# Signal Skill Canary V1",
        "",
        f"- variant: `{variant_id}`",
        f"- sample_count: `{len(canary_outputs)}`",
        "",
    ]
    improved = 0
    for item in canary_outputs:
        case_id = item["eval_case_id"]
        base_pred = baseline_map[case_id]
        canary_pred = canary_map[case_id]
        if (not base_pred["overall_pass"]) and canary_pred["overall_pass"]:
            improved += 1
        rows.extend(
            [
                f"## `{case_id}`",
                "",
                f"- baseline: `{'pass' if base_pred['overall_pass'] else 'fail'}` / {base_pred['failure_tags']}",
                f"- canary: `{'pass' if canary_pred['overall_pass'] else 'fail'}` / {canary_pred['failure_tags']}",
                "",
                "### baseline",
                "",
                f"- title: {base_output_map[case_id]['baseline_output']['title']}",
                f"- summary_line: {base_output_map[case_id]['baseline_output']['summary_line']}",
                f"- why_now: {base_output_map[case_id]['baseline_output']['why_now']}",
                "",
                "### canary",
                "",
                f"- title: {item['baseline_output']['title']}",
                f"- summary_line: {item['baseline_output']['summary_line']}",
                f"- why_now: {item['baseline_output']['why_now']}",
                "",
            ]
        )
    rows[3:3] = [f"- improved: `{improved}`"]
    return "\n".join(rows).strip() + "\n"


__all__ = ["build_canary_report", "load_jsonl", "select_canary_cases"]
