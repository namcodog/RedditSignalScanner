from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from backend.scripts.hotpost import build_v13_shadow_review_sheet as mod
from backend.scripts.hotpost import run_v13_published_shadow_refresh as shadow


def test_export_review_sheet_writes_editable_rows(tmp_path: Path) -> None:
    plan_path = tmp_path / "shadow.json"
    plan_path.write_text(json.dumps(_plan([_row("card-1")]), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "review.csv"

    result = mod.export_review_sheet([plan_path], output)

    assert result["rows"] == 1
    rows = _read_csv(output)
    assert rows[0]["source_plan"] == str(plan_path)
    assert rows[0]["card_id"] == "card-1"
    assert rows[0]["review_status"] == "approved"
    assert rows[0]["semantic_core_scene"] == "销售团队在讨论 CRM 回填负担。"
    assert "全部 CRM 都失败" in rows[0]["semantic_avoid_claims"]
    assert rows[0]["v13_title"] == "新版标题"
    assert rows[0]["edit_title"] == ""


def test_export_review_sheet_can_dedupe_card_id_by_latest_plan(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(_plan([_row("card-1")]), ensure_ascii=False), encoding="utf-8")
    latest_row = _row("card-1")
    latest_row["refreshed_card"]["title"] = "补跑新版标题"
    second.write_text(json.dumps(_plan([latest_row]), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "review.csv"

    result = mod.export_review_sheet([first, second], output, dedupe_card_id=True)

    assert result["rows"] == 1
    rows = _read_csv(output)
    assert rows[0]["source_plan"] == str(second)
    assert rows[0]["v13_title"] == "补跑新版标题"


def test_build_plan_from_review_sheet_applies_edits_and_skips_rejects(tmp_path: Path) -> None:
    plan_path = tmp_path / "shadow.json"
    plan_path.write_text(
        json.dumps(_plan([_row("card-1"), _row("card-2")]), ensure_ascii=False),
        encoding="utf-8",
    )
    review = tmp_path / "review.csv"
    mod.export_review_sheet([plan_path], review)
    rows = _read_csv(review)
    rows[0]["review_status"] = "edit"
    rows[0]["edit_title"] = "开发者把 AI 代码审查前置，避免大仓库改动越改越乱"
    rows[0]["edit_summary_line"] = "开发者开始把 AI 代码审查提前到改动前，而不是等出错后再补救。"
    rows[1]["review_status"] = "reject"
    _write_csv(review, rows)
    output_plan = tmp_path / "human-approved.json"

    result = mod.build_plan_from_review_sheet(review, output_plan)

    assert result["selected"] == 1
    assert result["skipped"] == 1
    plan = json.loads(output_plan.read_text(encoding="utf-8"))
    card = plan["cards"][0]["refreshed_card"]
    assert card["card_id"] == "card-1"
    assert card["title"] == "开发者把 AI 代码审查前置，避免大仓库改动越改越乱"
    assert card["summary_line"] == "开发者开始把 AI 代码审查提前到改动前，而不是等出错后再补救。"


def test_build_plan_from_review_sheet_rejects_quality_issues(tmp_path: Path) -> None:
    plan_path = tmp_path / "shadow.json"
    plan_path.write_text(json.dumps(_plan([_row("card-1")]), ensure_ascii=False), encoding="utf-8")
    review = tmp_path / "review.csv"
    mod.export_review_sheet([plan_path], review)
    rows = _read_csv(review)
    rows[0]["edit_title"] = "评估AI自动化"
    _write_csv(review, rows)

    with pytest.raises(ValueError, match="quality issues"):
        mod.build_plan_from_review_sheet(review, tmp_path / "human-approved.json")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mod.REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _plan(rows: list[dict]) -> dict:
    return {
        "kind": shadow.PLAN_KIND,
        "plan_version": shadow.PLAN_VERSION,
        "profile_id": shadow.V13_PROFILE_ID,
        "selected": len(rows),
        "generated": len(rows),
        "failed": 0,
        "cards": rows,
    }


def _row(card_id: str) -> dict:
    original = _published_card(card_id)
    refreshed = {**original, "title": "新版标题", "summary_line": "新版摘要"}
    return {
        "card_id": card_id,
        "lane": original["lane"],
        "card_type": original["card_type"],
        "profile_id": shadow.V13_PROFILE_ID,
        "semantic_model": "google/gemini-3-flash-preview",
        "writer_model": "deepseek/deepseek-v4-pro",
        "semantic_brief": {
            "core_scene": "销售团队在讨论 CRM 回填负担。",
            "writing_focus": "讲清楚这一步到底帮不帮销售赢单。",
            "risk_bounds": "不能说全部 CRM 都失败。",
            "avoid_claims": ["不要写成全部 CRM 都失败。"],
        },
        "original_card": original,
        "v12_shadow": {},
        "refreshed_card": refreshed,
        "changed": {"title": {"before": original["title"], "after": "新版标题"}},
        "fluency_repair_issue_count": 0,
        "remaining_density_issues": [],
        "v13_title_issues_before": [],
        "v13_title_issues_after": [],
        "error": "",
    }


def _published_card(card_id: str) -> dict:
    return {
        "card_id": card_id,
        "card_type": "validate",
        "lane": "signal",
        "title": "旧标题",
        "summary_line": "旧摘要",
        "audience": "旧读者",
        "why_now": "旧为什么现在看",
        "source_link": "https://reddit.test/q1",
        "detail": {"why_test_now": "旧证据判断"},
    }
