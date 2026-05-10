"""Three-tab Hotpost prompt A/B v12 high-density concise comparison.

V11 is the baseline. V12 keeps the generated facts and fields, then runs a
Chinese editing pass on the fields users read first. The goal is lower reading
load with the same information density, not shorter copy for its own sake.
Production prompts are untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v11 as v11


REPORTS_EVALS_DIR = v11.REPORTS_EVALS_DIR
WRITER_MODEL = v11.WRITER_MODEL
V11_RESULTS_PATH = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v11_chinese_fluency_results.json"

CONCISE_TARGET_FIELDS = {
    "title",
    "summary_line",
    "why_now",
    "why_test_now",
    "continue_signal",
    "stop_signal",
    "flashpoint",
    "fight_line",
}

FIELD_CHAR_LIMITS = {
    "title": 34,
    "summary_line": 62,
    "why_now": 86,
    "why_test_now": 78,
    "continue_signal": 58,
    "stop_signal": 62,
    "flashpoint": 78,
    "fight_line": 76,
}

VERBOSE_MARKERS = (
    "这说明",
    "这改变了",
    "这句话把",
    "下一步",
    "应该先",
    "直接说明了",
    "直接点出了",
    "已经从",
    "转移到了",
    "真正",
)

CLICKBAIT_COMPRESSION_WORDS = (
    "梦碎",
    "翻车",
    "炸了",
    "神了",
    "封神",
)


def load_v11_baseline_rows(path: Path = V11_RESULTS_PATH) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("v11 results must be a list")
    by_card_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        card_id = str(row.get("card_id") or "")
        if card_id:
            by_card_id[card_id] = row
    return by_card_id


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def find_v12_density_issues(generated: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in sorted(CONCISE_TARGET_FIELDS):
        for text in _iter_strings(generated.get(field)):
            limit = FIELD_CHAR_LIMITS[field]
            marker_hits = [marker for marker in VERBOSE_MARKERS if marker in text]
            if marker_hits and len(text) > max(26, int(limit * 0.72)):
                issues.append(f"{field}: 有低密度连接或解释词 {marker_hits[:3]}，需要把判断说得更直。")
            clickbait_hits = [word for word in CLICKBAIT_COMPRESSION_WORDS if word in text]
            if clickbait_hits:
                issues.append(f"{field}: 出现标题党式压缩词 {clickbait_hits[:3]}，需要改成具体发生了什么。")
    return issues


def _target_payload(generated: dict[str, Any]) -> dict[str, Any]:
    return {field: generated[field] for field in sorted(CONCISE_TARGET_FIELDS) if field in generated}


def build_high_density_repair_messages(
    *,
    generated: dict[str, Any],
    semantic_brief: dict[str, Any],
    issues: list[str],
) -> list[dict[str, str]]:
    issue_text = "\n".join(f"- {issue}" for issue in issues[:20])
    target_fields = _target_payload(generated)
    system = """
你是中文卡片的信息密度编辑。目标是减少阅读负担，不是压缩信息。

硬要求：
- 只输出 JSON，不输出解释。
- 只改 target_fields 里的字段；其他字段不要输出。
- 不新增字段，不删除 target_fields 中已有字段。
- 不新增事实，不扩大判断，不删关键证据。
- 不是压缩信息；要保留核心判断、必要证据和具体对象。
- 提升信息密度：删重复解释、铺垫、报告式连接词，把核心意思前置。
- 每个字段只讲一个主要判断；能一句说清就不要写成两层解释。
- why_now 只回答“现在变了什么”和“哪条证据说明变了”；不要顺手给行动建议。
- 不要为了短而写成口号、标题党或空泛结论。
- 禁止用“梦碎、翻车、炸了、神了、封神”这类情绪词换取简洁；要写具体发生了什么。
- 英文缩写和产品名保持可读排版，例如“AI 代理”“AI SEO”“Claude”，不要挤成“全自动AI代理”。
- 避免“这说明、这改变了、直接点出、转移到了、值得关注”等解释腔。
- 标点服务理解：必要时用冒号或分号切开，但不要把一句话拆成零碎短句。
- 保持 V11 已修好的自然中文，不能出现死物主语做人类动作。
""".strip()
    payload = {
        "semantic_brief": semantic_brief,
        "target_fields": target_fields,
        "all_current_fields_for_context": generated,
        "field_char_guidance": FIELD_CHAR_LIMITS,
        "density_issues": issues,
        "task": "只改 target_fields，把重点字段改得更短读、更直达、更高信息密度；不删关键证据，只输出 target_fields 的 JSON。",
        "bad_examples": [
            "这说明判断依据已经从提示词本身，转移到了数据接入能力上。",
            "这句话把AI公司的成功和开发者的无偿贡献直接对立起来，引爆了关于数据所有权的讨论。",
            "所以，下一步选工具或优化流程，应该先看它能不能连上你的代码和数据，而不是先研究提示词技巧。",
        ],
        "better_examples": [
            "判断重点变了：不是提示词，而是能不能接入真实数据。",
            "最高赞评论把矛盾说透了：AI 公司用社区免费代码训练模型，反过来威胁开发者工作。",
            "选 AI SEO 工具时，先看它能不能接入网站代码和搜索数据。",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": issue_text + "\n\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ]


def merge_target_field_repairs(original: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    merged = dict(original)
    if not isinstance(repaired, dict):
        return merged
    for field in CONCISE_TARGET_FIELDS:
        if field not in repaired or field not in original:
            continue
        if isinstance(original[field], list):
            if isinstance(repaired[field], list):
                merged[field] = repaired[field]
        elif isinstance(repaired[field], str):
            merged[field] = repaired[field]
    return merged


async def repair_high_density_concise(
    original: dict[str, Any],
    *,
    semantic_brief: dict[str, Any],
    issues: list[str],
    model: str,
) -> dict[str, Any]:
    repaired = await v1._generate_json(
        model=model,
        timeout=90.0,
        messages=build_high_density_repair_messages(
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
    return merge_target_field_repairs(original, repaired)


def render_v12_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v7.render_v7_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v12 high-density-concise 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v12_high_density_concise_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v12_high_density_concise_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v12_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(*, writer_model: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_label = "v11 baseline vs v12 high-density-concise"
    for source in load_v11_baseline_rows().values():
        baseline = source.get("variant") or {}
        semantic_brief = source.get("semantic_brief") or {}
        variant = dict(baseline)
        variant_error = ""
        issues_before = find_v12_density_issues(variant)
        issues_after: list[str] = []
        try:
            if issues_before:
                variant = await repair_high_density_concise(
                    variant,
                    semantic_brief=semantic_brief,
                    issues=issues_before,
                    model=writer_model,
                )
            issues_after = find_v12_density_issues(variant)
            if issues_after:
                variant = await repair_high_density_concise(
                    variant,
                    semantic_brief=semantic_brief,
                    issues=issues_after,
                    model=writer_model,
                )
                issues_after = find_v12_density_issues(variant)
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
                "v12_density_issues_before": issues_before,
                "v12_density_issues_after": issues_after,
            }
        )
        print(
            json.dumps(
                {
                    "event": "generated",
                    "lane": source.get("lane"),
                    "card_id": source.get("card_id"),
                    "model": model_label,
                    "density_issue_count_before": len(issues_before),
                    "density_issue_count_after": len(issues_after),
                    "variant_error": variant_error,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v12 high-density concise")
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
