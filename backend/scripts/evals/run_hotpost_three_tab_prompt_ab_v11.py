"""Three-tab Hotpost prompt A/B v11 Chinese fluency repair comparison.

V10 is the baseline. V11 keeps the generated facts and fields, then runs a
Chinese fluency repair pass focused on subject-verb fit, dead-object subjects,
and sentence-level readability. Production prompts are untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v10 as v10


REPORTS_EVALS_DIR = v10.REPORTS_EVALS_DIR
WRITER_MODEL = v10.WRITER_MODEL
V10_RESULTS_PATH = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v10_reddit_context_results.json"

DEAD_OBJECT_HUMAN_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("工具开始强调", "工具是死物，不能开始强调；改成厂商开始宣传、产品页面开始主打，或用户开始要求。"),
    ("产品开始强调", "产品是死物，不能开始强调；改成厂商开始宣传或产品页面开始主打。"),
    ("方案开始强调", "方案是死物，不能开始强调；改成团队开始强调或卖方开始宣传。"),
    ("能力开始成为", "能力作主语太抽象；改成用户开始把某种能力当成判断标准。"),
    ("讨论开始意识到", "讨论不能意识到；改成用户开始意识到、评论区开始转向。"),
)
ABSTRACT_NOUN_STACK_RE = re.compile(r"(?:数据连接功能|投入方向|成本变化|能力变化|方案变化)")


def load_v10_baseline_rows(path: Path = V10_RESULTS_PATH) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("v10 results must be a list")
    by_card_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        card_id = str(row.get("card_id") or "")
        if card_id:
            by_card_id[card_id] = row
    return by_card_id


def find_v11_fluency_issues(generated: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field, value in generated.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            for pattern, reason in DEAD_OBJECT_HUMAN_ACTION_PATTERNS:
                if pattern in item:
                    issues.append(f"{field}: 死物主语做人类动作 `{pattern}`；{reason}")
            for match in ABSTRACT_NOUN_STACK_RE.findall(item):
                issues.append(f"{field}: 抽象名词堆叠 `{match}`，需要改成谁在做什么、花多少钱、要接什么数据。")
    return issues


def build_chinese_fluency_repair_messages(
    *,
    generated: dict[str, Any],
    semantic_brief: dict[str, Any],
    issues: list[str],
) -> list[dict[str, str]]:
    issue_text = "\n".join(f"- {issue}" for issue in issues[:16])
    system = """
你是中文卡片顺读编辑，只修中文语法、主语和动词搭配，不改事实。

硬要求：
- 只输出 JSON，不输出解释。
- 保持输入 JSON 的字段和结构，不新增字段，不删除字段。
- 不新增事实，不扩大判断，只基于 semantic_brief 和 current_generated_fields 改写。
- 优先修“读起来不顺”的中文，而不是追求更短或更漂亮。
- 修掉死物主语做人类动作：不要写“工具开始强调”“方案开始意识到”“产品开始认为”。
- 遇到死物主语，要改成真实主语：用户、评论区、开发者、团队、厂商、产品页面、服务商。
- “工具开始强调”通常应改成“厂商开始宣传”“产品页面开始主打”或“用户开始要求”。
- 例：不要写“工具开始强调自己的数据连接功能”；改成“更多厂商开始宣传：工具能接入网站代码和搜索数据”。
- 例：不要写“方案的成本变化”；改成“用户接入这些数据要花多少时间和钱”。
- 句子要能顺口读出来；一口气读不顺，就拆句或换主语。
- 避免名词堆叠、抽象动作和报告腔。
""".strip()
    payload = {
        "semantic_brief": semantic_brief,
        "current_generated_fields": generated,
        "required_fields": list(generated.keys()),
        "fluency_issues": issues,
        "task": "只修 fluency_issues 指出的中文顺读、主语和动词搭配问题；字段不变，只输出修正后的完整 JSON。",
        "bad_examples": [
            "工具开始强调自己的数据连接功能",
            "方案开始体现出成本变化",
            "讨论意识到投入方向需要变化",
        ],
        "better_examples": [
            "更多厂商开始宣传：工具能接入网站代码和搜索数据",
            "用户开始追问：接入这些数据到底要花多少时间和钱",
            "评论区开始转向：还值不值得继续投入",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": issue_text + "\n\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ]


async def repair_chinese_fluency(
    original: dict[str, Any],
    *,
    semantic_brief: dict[str, Any],
    issues: list[str],
    model: str,
) -> dict[str, Any]:
    repaired = await v1._generate_json(
        model=model,
        timeout=90.0,
        messages=build_chinese_fluency_repair_messages(
            generated=original,
            semantic_brief=semantic_brief,
            issues=issues,
        ),
        client_factory=lambda selected_model, selected_timeout: v1.build_card_content_client(
            selected_model,
            timeout=selected_timeout,
        ),
        max_tokens=4096,
        response_schema=None,
    )
    return v7.merge_repaired_fields(original, repaired)


def render_v11_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v7.render_v7_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v11 chinese-fluency 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v11_chinese_fluency_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v11_chinese_fluency_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v11_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(*, writer_model: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_label = "v10 baseline vs v11 chinese-fluency"
    for source in load_v10_baseline_rows().values():
        baseline = source.get("variant") or {}
        semantic_brief = source.get("semantic_brief") or {}
        variant = dict(baseline)
        variant_error = ""
        issues_before = find_v11_fluency_issues(variant)
        issues_after: list[str] = []
        try:
            if issues_before:
                variant = await repair_chinese_fluency(
                    variant,
                    semantic_brief=semantic_brief,
                    issues=issues_before,
                    model=writer_model,
                )
            issues_after = find_v11_fluency_issues(variant)
            if issues_after:
                raise ValueError("v11 fluency issues remain: " + "; ".join(issues_after[:8]))
        except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
            variant_error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "lane": source.get("lane"),
                "card_id": source.get("card_id"),
                "model": model_label,
                "published": source.get("published") or {},
                "semantic_brief": semantic_brief,
                "baseline": baseline,
                "variant": variant,
                "baseline_error": source.get("variant_error") or "",
                "variant_error": variant_error,
                "v11_fluency_issues_before": issues_before,
                "v11_fluency_issues_after": issues_after,
            }
        )
        print(
            json.dumps(
                {
                    "event": "generated",
                    "lane": source.get("lane"),
                    "card_id": source.get("card_id"),
                    "model": model_label,
                    "fluency_issue_count_before": len(issues_before),
                    "fluency_issue_count_after": len(issues_after),
                    "variant_error": variant_error,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v11 chinese-fluency")
    parser.add_argument("--writer-model", default=WRITER_MODEL)
    args = parser.parse_args()

    rows = await run_experiment(writer_model=args.writer_model.strip() or WRITER_MODEL)
    json_path, md_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
