"""Three-tab Hotpost prompt A/B v2 comparison.

This runner keeps the v1 experiment as negative evidence and runs a new
read-only variant based on the user-approved v2 calibration baseline.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1


REPORTS_EVALS_DIR = v1.REPORTS_EVALS_DIR
LANE_ORDER = v1.LANE_ORDER


def build_v2_baseline_overlay() -> str:
    return """

## 本轮 A/B 变体：v2 baseline，普通用户一眼能懂

不新增字段，不改字段名，不改 JSON 结构。只改变写法。必须输出完整、合法 JSON。

核心目标：
- 用户不懂 Reddit、不懂广告后台、不懂 AI 工程词，也要能看懂。
- 克制、清楚、像认真做信息判断的人写给业务同事看。
- 只基于证据，不补新信息，不扩大成行业共识。
- 不要短视频解说、营销号、段子手或装熟口吻。
- 不允许多张卡套同一套话。

title：
- 像一句普通人能直接读懂的话，只看标题也知道大概在讲什么。
- 不套固定结构，不写报告标题。
- 少用抽象词，多写人能感到的成本、风险、信任、时间、是否能落地。
- 好标题示例：
  - AI 做 SEO，光写提示词不够，还得看网站代码和搜索数据
  - 想用 AI 自动干活，先别忘了调教时间和模型账单
  - 程序员不满 AI 写代码：它学的正是大家免费留下的代码和问答
  - 全自动 AI 工具很难上线，小错误太多，开发者修不过来
  - 写了 800 行提示词，结果只是个普通轮播，评论区不买账
  - 模型跑分高不一定好用，服务商给你的可能是缩水版

summary_line / why_now / detail：
- 把英文黑话、工程词、社区梗翻成普通后果：成本、风险、信任、时间、是否能落地。
- 每个字段只承担自己的信息，不互相复读。
- why_now 只解释“现在为什么值得看”，不要重讲痛点。
- why_test_now 只解释哪条证据撑住判断，不给动作建议。

硬禁区：
- 不写“这帖火了 / 火的原因 / 火在 / 值得关注 / 引发热议”。
- 不把“以前……现在……”或“不是……而是……”当默认结构。
- 不用“本质、反映、赛道、生态、核心矛盾、趋势变化”撑句子。
""".strip()


def render_v2_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v1.render_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v2 baseline 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v2_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v2_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v2_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(*, limit_per_lane: int, model_override: str | None) -> list[dict[str, Any]]:
    original_overlay = v1.build_plain_language_overlay
    v1.build_plain_language_overlay = build_v2_baseline_overlay
    try:
        return await v1.run_experiment(limit_per_lane=limit_per_lane, model_override=model_override)
    finally:
        v1.build_plain_language_overlay = original_overlay


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v2 baseline")
    parser.add_argument("--limit-per-lane", type=int, default=2)
    parser.add_argument("--model", default="", help="Optional model override for all lanes")
    args = parser.parse_args()

    rows = await run_experiment(
        limit_per_lane=args.limit_per_lane,
        model_override=args.model.strip() or None,
    )
    json_path, md_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
