"""Three-tab Hotpost prompt A/B v7 concise one-glance comparison.

Gemini Flash produces the semantic brief. Qwen writes the final Chinese card
fields with extra constraints for concise, accurate, one-glance copy. This
read-only runner writes distinct v7 artifacts and leaves production prompts
untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v3 as v3
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v4 as v4
from app.services.llm.interfaces import LLMClientError


REPORTS_EVALS_DIR = v4.REPORTS_EVALS_DIR
SEMANTIC_MODEL = "google/gemini-3-flash-preview"
WRITER_MODEL = "qwen/qwen3.6-max-preview"
BASELINE_MODEL = v4.BASELINE_MODEL
ENGLISH_ALLOWED_TERMS = {
    "AI",
    "SEO",
    "API",
    "LLM",
    "LLMs",
    "GitHub",
    "StackOverflow",
    "Search",
    "Console",
    "Claude",
    "Demo",
    "Bot",
    "Agent",
    "Reddit",
    "Qwen",
    "Gemini",
}
REPORT_TONE_PATTERNS = (
    "原话里有个关键句",
    "关键证据是那句",
    "关键证据是“",
    "判断顺序从",
    "判断重点转向",
    "讨论焦点变化",
    "值得关注",
    "这帖火了",
    "火的原因",
)
KEYWORD_WATCH_RE = re.compile(r"继续看[^。]*(?:这些词|关键词|单个词)")
ENGLISH_FRAGMENT_RE = re.compile(
    r"[A-Za-z][A-Za-z+\-']{2,}(?:\s+[A-Za-z][A-Za-z+\-']{1,}){1,}|[A-Za-z]{5,}"
)


def build_concise_writer_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    instruction = """

## V7 精简一眼懂规则

这次不是把话写得更口语，而是写得更短、更准、更容易第一眼看懂。

硬要求：
- 保持原 JSON 字段和结构不变，不新增字段。
- 不新增事实，不把证据没有证明的事写成结论。
- 不能为了短而丢掉关键意思；先保证意思对，再压缩字数。
- title 单独看也要知道谁遇到什么问题，或这件事为什么值得点开。
- summary_line 只讲一个核心判断，用一个最关键的证据撑住。
- why_now 只回答“现在变了什么”，不要重复痛点，也不要写成长解释。
- why_test_now 只说哪条证据撑住判断，不给动作建议。
- audience / target_user_and_scene 写成“谁在什么场景下”，少用宽泛人群词。
- 每个字段删掉绕弯话、重复解释、报告腔词和需要咬文嚼字的复句。
- 除 quote_pack 这种原本需要双语引用的字段外，不要输出英文长句、截断英文引用或零散英文碎片；用中文转述证据。
- continue_signal / stop_signal 只能观察后续用户行为、成本变化、产品变化或讨论走向，不能观察关键词、英文残片或单个词是否继续出现。
- why_test_now 不要写“原话里有个关键句”“关键证据是那句”这类报告腔，直接用中文说明哪条证据撑住判断。
- 可保留必要专名，如 AI、SEO、API、LLM、GitHub、StackOverflow、Search Console、Claude；不要保留没有解释价值的英文半句。

自检：
- 用户扫一眼能不能懂？
- 句子是不是可以再短 20%，但意思不变？
- 有没有“判断重点转向、讨论焦点变化、值得关注”这类空转表达？
""".rstrip()
    return [{**messages[0], "content": messages[0]["content"] + instruction}, *messages[1:]]


def _english_fragment_has_only_allowed_terms(fragment: str) -> bool:
    words = set(re.findall(r"[A-Za-z]+", fragment))
    return bool(words) and words <= ENGLISH_ALLOWED_TERMS


def find_v7_copy_issues(generated: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field, value in generated.items():
        if field == "quote_pack":
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            for pattern in REPORT_TONE_PATTERNS:
                if pattern in item:
                    issues.append(f"{field}: 报告腔或模板化表达 `{pattern}`")
            if KEYWORD_WATCH_RE.search(item):
                issues.append(f"{field}: 不能写关键词观察")
            for fragment in ENGLISH_FRAGMENT_RE.findall(item):
                if not _english_fragment_has_only_allowed_terms(fragment):
                    issues.append(f"{field}: 英文长句或英文碎片 `{fragment}`")
    return issues


def merge_repaired_fields(original: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field, value in original.items():
        candidate = repaired.get(field)
        if isinstance(value, str):
            merged[field] = candidate if isinstance(candidate, str) and candidate.strip() else value
        elif isinstance(value, list):
            merged[field] = candidate if isinstance(candidate, list) and candidate else value
        elif isinstance(value, dict):
            merged[field] = candidate if isinstance(candidate, dict) and candidate else value
        else:
            merged[field] = candidate if candidate is not None else value
    return merged


def _with_v7_copy_retry_instruction(messages: list[dict[str, str]], issues: list[str]) -> list[dict[str, str]]:
    issue_text = "\n".join(f"- {issue}" for issue in issues[:12])
    retry_note = f"""

## V7 文案质量重写

上一次输出没有通过卡片文案检查：
{issue_text}

请只重写这些不合格表达，保持同一 JSON 字段和结构。
- 非 quote_pack 字段不要粘贴英文长句或截断引文，全部改成中文转述。
- 不要写“原话里有个关键句”“关键证据是那句”“判断顺序从”。
- continue_signal 只观察后续真实行为、案例、成本、产品变化或讨论走向，不能观察关键词。
- 保留事实边界，压短句子，让用户一眼懂。
""".rstrip()
    return [{**messages[0], "content": messages[0]["content"] + retry_note}, *messages[1:]]


def build_v7_copy_repair_messages(
    *,
    generated: dict[str, Any],
    semantic_brief: dict[str, Any],
    issues: list[str],
) -> list[dict[str, str]]:
    system = """
你是中文质检改写编辑，只负责把已经生成的卡片字段改得更清楚、更短、更像人话。

硬要求：
- 只输出 JSON，不输出解释。
- 必须输出完整 JSON，包含 required_fields 里的每一个字段；不能只返回被修改字段。
- 保持输入 JSON 的字段和结构，不新增字段；每个字符串字段都必须非空。
- 不新增事实，只基于 semantic_brief 和当前字段改写。
- 不要引用或粘贴原始英文，不要输出英文长句、截断英文引用或英文碎片。
- 不写“原话里有个关键句”“关键证据是那句”“判断顺序从”。
- continue_signal 只能写后续可观察的真实行为、案例、成本、产品变化或讨论走向，不能写观察关键词。
- 每个字段先保证意思准确，再压短到用户一眼能懂。
""".strip()
    payload = {
        "semantic_brief": semantic_brief,
        "current_generated_fields": generated,
        "required_fields": list(generated.keys()),
        "copy_issues": issues,
        "task": "修正 copy_issues 指出的字段；字段不变，只输出修正后的 JSON。",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ]


async def repair_v7_copy_fields(
    original: dict[str, Any],
    *,
    semantic_brief: dict[str, Any],
    issues: list[str],
    model: str,
    timeout: float,
    max_tokens: int,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    repaired_payload = await v1._generate_json(
        model=model,
        timeout=timeout,
        messages=build_v7_copy_repair_messages(
            generated=original,
            semantic_brief=semantic_brief,
            issues=issues,
        ),
        client_factory=lambda selected_model, selected_timeout: v1.build_card_content_client(
            selected_model,
            timeout=selected_timeout,
        ),
        max_tokens=max_tokens,
        response_schema=response_schema,
    )
    return merge_repaired_fields(original, repaired_payload)


async def generate_semantic_brief_with_retry(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    last_error: ValueError | LLMClientError | None = None
    for _ in range(3):
        try:
            return await v4.generate_semantic_brief(
                lane=lane,
                card_id=card_id,
                published=published,
                baseline=baseline,
                variant_v3=variant_v3,
                model=model,
            )
        except (ValueError, LLMClientError) as exc:
            last_error = exc
            await asyncio.sleep(1)
    raise last_error or ValueError("semantic brief is empty")


async def generate_one_two_stage(
    draft: v1.ValidationCardDraft | v1.WritingCardDraft,
    *,
    card: dict[str, Any],
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    baseline_model: str,
    semantic_model: str,
    writer_model: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    card_id = str(card.get("card_id") or "")
    lane = str(card.get("lane") or "")
    print(json.dumps({"event": "phase", "phase": "baseline_start", "lane": lane, "card_id": card_id}, ensure_ascii=False), flush=True)
    baseline, _ = await v1.generate_one(
        draft,
        rules=rules,
        models=models,
        banned=banned,
        variant=True,
        model_override=baseline_model,
    )
    print(json.dumps({"event": "phase", "phase": "baseline_done", "lane": lane, "card_id": card_id}, ensure_ascii=False), flush=True)
    writer_base_messages = v1._with_overlay(
        v1._messages_for_draft(draft, rules=rules, banned=banned),
        enabled=True,
    )
    model, timeout, max_tokens, schema = v1._model_route_for_draft(
        draft,
        rules=rules,
        models=models,
        model_override=writer_model,
    )
    published = v1._published_fields(card)
    print(json.dumps({"event": "phase", "phase": "semantic_start", "lane": lane, "card_id": card_id}, ensure_ascii=False), flush=True)
    semantic_brief = await generate_semantic_brief_with_retry(
        lane=lane,
        card_id=card_id,
        published=published,
        baseline=baseline,
        variant_v3=baseline,
        model=semantic_model,
    )
    print(json.dumps({"event": "phase", "phase": "semantic_done", "lane": lane, "card_id": card_id}, ensure_ascii=False), flush=True)
    writer_messages = v4.build_writer_messages(writer_base_messages, semantic_brief=semantic_brief)
    writer_messages = build_concise_writer_messages(writer_messages)
    print(
        json.dumps(
            {"event": "phase", "phase": "writer_start", "lane": lane, "card_id": card_id, "attempt": 1},
            ensure_ascii=False,
        ),
        flush=True,
    )
    variant = await v4._generate_fields_from_messages(
        draft,
        rules=rules,
        messages=writer_messages,
        model=model,
        max_tokens=max_tokens,
        response_schema=schema,
        timeout=timeout,
    )
    issues = find_v7_copy_issues(variant)
    print(
        json.dumps(
            {
                "event": "phase",
                "phase": "writer_done",
                "lane": lane,
                "card_id": card_id,
                "attempt": 1,
                "copy_issue_count": len(issues),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    for repair_attempt in range(2):
        if not issues:
            break
        print(
            json.dumps(
                {
                    "event": "phase",
                    "phase": "repair_start",
                    "lane": lane,
                    "card_id": card_id,
                    "attempt": repair_attempt + 1,
                    "copy_issue_count": len(issues),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        variant = await repair_v7_copy_fields(
            variant,
            semantic_brief=semantic_brief,
            issues=issues,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
            response_schema=schema,
        )
        issues = find_v7_copy_issues(variant)
        print(
            json.dumps(
                {
                    "event": "phase",
                    "phase": "repair_merge_done",
                    "lane": lane,
                    "card_id": card_id,
                    "attempt": repair_attempt + 1,
                    "copy_issue_count": len(issues),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if not issues:
            break
    if issues:
        raise ValueError("v7 copy issues remain: " + "; ".join(issues[:8]))
    return baseline, variant, semantic_brief


def render_v7_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v4.render_v4_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v4 two-stage 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v7_concise_qwen_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v7_concise_qwen_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v7_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(
    *,
    limit_per_lane: int,
    baseline_model: str,
    semantic_model: str,
    writer_model: str,
) -> list[dict[str, Any]]:
    original_overlay = v1.build_plain_language_overlay
    v1.build_plain_language_overlay = v3.build_v3_semantic_overlay
    try:
        samples = v1.load_sample_cards(limit_per_lane=limit_per_lane)
        rules = v4.with_v4_banned_patterns(v1.load_card_content_rules())
        models = v1.load_card_content_models()
        banned = v1._all_banned_patterns(rules)
        rows: list[dict[str, Any]] = []
        model_label = f"{semantic_model} -> {writer_model}"
        for lane in v1.LANE_ORDER:
            for card in samples[lane]:
                draft = v1.card_to_draft(card)
                baseline: dict[str, Any] = {}
                variant: dict[str, Any] = {}
                semantic_brief: dict[str, Any] = {}
                baseline_error = ""
                variant_error = ""
                try:
                    baseline, variant, semantic_brief = await generate_one_two_stage(
                        draft,
                        card=card,
                        rules=rules,
                        models=models,
                        banned=banned,
                        baseline_model=baseline_model,
                        semantic_model=semantic_model,
                        writer_model=writer_model,
                    )
                except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
                    variant_error = f"{type(exc).__name__}: {exc}"
                rows.append(
                    {
                        "lane": lane,
                        "card_id": card["card_id"],
                        "model": model_label,
                        "published": v1._published_fields(card),
                        "semantic_brief": semantic_brief,
                        "baseline": baseline,
                        "variant": variant,
                        "baseline_error": baseline_error,
                        "variant_error": variant_error,
                    }
                )
                print(
                    json.dumps(
                        {
                            "event": "generated",
                            "lane": lane,
                            "card_id": card["card_id"],
                            "model": model_label,
                            "variant_error": variant_error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        return rows
    finally:
        v1.build_plain_language_overlay = original_overlay


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v7 concise-qwen")
    parser.add_argument("--limit-per-lane", type=int, default=2)
    parser.add_argument("--baseline-model", default=BASELINE_MODEL)
    parser.add_argument("--semantic-model", default=SEMANTIC_MODEL)
    parser.add_argument("--writer-model", default=WRITER_MODEL)
    args = parser.parse_args()

    rows = await run_experiment(
        limit_per_lane=args.limit_per_lane,
        baseline_model=args.baseline_model.strip() or BASELINE_MODEL,
        semantic_model=args.semantic_model.strip() or SEMANTIC_MODEL,
        writer_model=args.writer_model.strip() or WRITER_MODEL,
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
