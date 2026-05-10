from __future__ import annotations

from scripts.acceptance.validate_warzone_live_matrix import validate_matrix


def _ok_row() -> dict[str, object]:
    return {
        "expected_warzone": "AI_Workflow",
        "status": "completed",
        "report_tier": "B_trimmed",
        "pain_titles": [
            "任务和知识散落在多处，协作推进情况很不透明",
            "流程一旦跨系统切换，信息和动作就容易断开",
            "任务很多，但真正推进情况并不清楚",
        ],
        "opportunity_titles": [
            "任务和知识散落在多处，协作推进情况很不透明的省事方案机会",
            "流程一旦跨系统切换，信息和动作就容易断开的省事方案机会",
        ],
        "community_titles": ["r/ChatGPT", "r/Notion"],
        "result_url": "http://127.0.0.1:3006/report/demo-task-id",
    }


def test_validate_matrix_accepts_clean_rows() -> None:
    payload = validate_matrix(rows=[_ok_row()], min_a_full=0, max_c_scouting=1)
    assert payload["accepted"] is True
    assert payload["issues"] == []


def test_validate_matrix_rejects_placeholder_pain_and_noise_opportunity() -> None:
    row = _ok_row()
    row["pain_titles"] = ["关键痛点 1", "高频抱怨", "任务很多，但真正推进情况并不清楚"]
    row["opportunity_titles"] = ["高频抱怨：Is seal deeper", "产品机会：need a mobile app"]
    payload = validate_matrix(rows=[row], min_a_full=0, max_c_scouting=1)
    issues = "\n".join(payload["issues"])
    assert payload["accepted"] is False
    assert "placeholder pain title=关键痛点 1" in issues
    assert "placeholder pain title=高频抱怨" in issues
    assert "low-signal opportunity title=高频抱怨：Is seal deeper" in issues


def test_validate_matrix_enforces_global_thresholds() -> None:
    row = _ok_row()
    row["report_tier"] = "C_scouting"
    payload = validate_matrix(rows=[row], min_a_full=1, max_c_scouting=0)
    issues = "\n".join(payload["issues"])
    assert payload["accepted"] is False
    assert "global: A_full count 0 < required 1" in issues
    assert "global: C_scouting count 1 > allowed 0" in issues


def test_validate_matrix_rejects_duplicate_and_nested_titles() -> None:
    row = _ok_row()
    row["pain_titles"] = [
        "任务和知识散落在多处，协作推进情况很不透明",
        "任务和知识散落在多处，协作推进情况很不透明",
        "流程一旦跨系统切换，信息和动作就容易断开",
    ]
    row["opportunity_titles"] = [
        "围绕「围绕「流程一旦跨系统切换，信息和动作就容易断开」反复出现的关键麻烦」的产品机会",
        "围绕「流程一旦跨系统切换，信息和动作就容易断开」的产品机会",
    ]
    payload = validate_matrix(rows=[row], min_a_full=0, max_c_scouting=1)
    issues = "\n".join(payload["issues"])
    assert payload["accepted"] is False
    assert "duplicate pain title=任务和知识散落在多处，协作推进情况很不透明" in issues
    assert "nested opportunity title=围绕「围绕「流程一旦跨系统切换，信息和动作就容易断开」反复出现的关键麻烦」的产品机会" in issues
