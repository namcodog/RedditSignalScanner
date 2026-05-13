"""Three-tab Hotpost prompt A/B v3 comparison.

This runner keeps v2 as prior evidence and adds the user's next feedback:
make semantic pauses clearer with punctuation and push the interpretation one
level deeper without changing the JSON contract.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1


REPORTS_EVALS_DIR = v1.REPORTS_EVALS_DIR
LANE_ORDER = v1.LANE_ORDER
V3_EXTRA_BANNED_PATTERNS = (
    "判断顺序从",
    "判断顺序改变",
    "这帖现在值得看",
)


def build_v3_semantic_overlay() -> str:
    return """

## 本轮 A/B 变体：v3，语义更顺、判断更深

不新增字段，不改字段名，不改 JSON 结构。只改变写法。必须输出完整、合法 JSON。

核心目标：
- 普通用户只看卡片，也要知道“这件事是什么、为什么重要、它改变了什么判断”。
- 不追求更口语。要克制、清楚、像真人编辑认真解释给业务同事听。
- 深度不是写抽象词，而是把证据背后的取舍讲出来：谁被什么卡住，为什么原来的看法不够用，下一步应该先看哪个关键条件。
- 只能从给定证据推出下一层含义；证据不够时，宁可写得窄一点，不补行业大判断。
- 不要明说“判断顺序改变了”。要直接写改变后的判断是什么，以及为什么这个条件更关键。

标点和停顿：
- 按语义加标点。一个句子里如果有“场景、转折、原因、结果、证据”两层以上，必须用逗号、冒号或分号切开。
- 不要把多个判断硬塞成一串长句。读者应该能顺着停顿读完，而不是读到一半再回头理解。
- 冒号只用来解释前一句，不要每个标题都用冒号。
- 中文里夹英文词时，英文只做锚点；前后要有清楚的中文解释。

title：
- 只看标题也要知道大概在讲什么。
- 标题可以用逗号、冒号或问号帮助理解，但不能变成统一格式。
- 避免“判断顺序从先……转成先……”这种机器味句式。
- 好标题示例：
  - AI 做 SEO，光写提示词不够；还得看网站代码和搜索数据
  - 想用 AI 自动干活，先算清调教时间和模型账单
  - 程序员不满 AI 写代码：它学的正是大家免费留下的代码和问答
  - 全自动 AI 工具很难上线，小错误太多，开发者修不过来
  - 写了 800 行提示词，结果只是个普通轮播，评论区不买账
  - 模型跑分高不一定好用，服务商给你的可能是缩水版

summary_line / why_now / detail：
- summary_line 先给清楚判断，再补一个最关键的原因或证据。
- why_now 只解释“现在为什么值得看”：哪里开始变了，或什么判断开始被重新排序。
- why_test_now 只解释哪条证据撑住判断。不要给动作建议，不要重复 why_now。
- 如果原话被截断、很长，或带 `...` / `…`，必须改成中文转述；输出里不要保留省略号。
- audience 只能写短句，优先用“想用 X 做 Y 的人/团队”或“在 X 场景下要做 Y 的人/团队”。不要加“尤其是、特别是、以及那些”后缀。
- target_user_and_scene 写成“谁在什么场景下”，不要写成宽泛身份标签。
- pain_point 先写人的后果，再补机制。不要先讲概念。
- continue_signal / stop_signal 要具体到“接下来观察什么会增强或削弱判断”，不要写空泛趋势。

硬禁区：
- 不写“这帖火了 / 火的原因 / 火在 / 值得关注 / 引发热议”。
- 不把“以前……现在……”或“不是……而是……”当默认结构。
- 不用“本质、反映、赛道、生态、核心矛盾、趋势变化”撑句子。
- 不写“特别是那些”，不要用宽泛补语把 audience 拉长。
- 不写“尤其是”“以及那些”，audience 里不要出现任何追加解释。
- 不写“判断顺序从”“判断顺序改变”“这帖现在值得看”。把它们改成具体判断。
- 不输出 `...` 或 `…`；残缺英文必须改成完整中文转述。
- 不连续使用同一种句式；不同卡片必须根据真实信息重新组织语义。
""".strip()


def render_v3_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v1.render_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v3 semantic baseline 小样本报告",
        1,
    )


def with_v3_banned_patterns(rules: dict[str, Any]) -> dict[str, Any]:
    patched = copy.deepcopy(rules)
    banned_patterns = patched.setdefault("banned_patterns", {})
    global_patterns = banned_patterns.setdefault("global", [])
    for pattern in V3_EXTRA_BANNED_PATTERNS:
        if pattern not in global_patterns:
            global_patterns.append(pattern)
    return patched


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v3_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v3_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v3_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(*, limit_per_lane: int, model_override: str | None) -> list[dict[str, Any]]:
    original_overlay = v1.build_plain_language_overlay
    original_load_rules = v1.load_card_content_rules
    v1.build_plain_language_overlay = build_v3_semantic_overlay

    def _v3_load_card_content_rules() -> dict[str, Any]:
        return with_v3_banned_patterns(original_load_rules())

    v1.load_card_content_rules = _v3_load_card_content_rules
    try:
        return await v1.run_experiment(limit_per_lane=limit_per_lane, model_override=model_override)
    finally:
        v1.build_plain_language_overlay = original_overlay
        v1.load_card_content_rules = original_load_rules


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v3 semantic baseline")
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
