"""Three-tab Hotpost prompt A/B v9 DeepSeek Flash semantic comparison.

DeepSeek V4 Flash produces the semantic brief through OpenRouter. MiMo v2.5 Pro
then writes the final Chinese card fields using the v7 concise copy gate. This
read-only runner writes distinct v9 artifacts and leaves production prompts
untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v3 as v3
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v4 as v4
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v5 as v5
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7
from app.services.llm.interfaces import LLMClientError


REPORTS_EVALS_DIR = v7.REPORTS_EVALS_DIR
SEMANTIC_MODEL = "deepseek/deepseek-v4-flash"
WRITER_MODEL = "xiaomi/mimo-v2.5-pro"
BASELINE_MODEL = v7.BASELINE_MODEL


def build_v9_writer_messages(
    messages: list[dict[str, str]],
    *,
    semantic_brief: dict[str, Any],
) -> list[dict[str, str]]:
    brief_text = json.dumps(semantic_brief, ensure_ascii=False, indent=2)
    instruction = f"""

## 语义理解层 brief

下面是语义理解层对英文 Reddit 证据的判断。你是中文字段编辑，只基于这个 brief 和原始输入生成中文字段。

{brief_text}

写作要求：
- 保持原 JSON 字段和结构不变。
- 中文字段要顺，按语义加标点，让用户能一眼读懂。
- 不要照抄 brief，要把它转成自然中文卡片。
- 不新增事实；brief 说不能夸大的地方，一律收窄。
""".rstrip()
    return [{**messages[0], "content": messages[0]["content"] + instruction}, *messages[1:]]


async def generate_semantic_brief_once(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    if model.startswith("google/") or model.startswith("gemini"):
        return await v4.generate_semantic_brief(
            lane=lane,
            card_id=card_id,
            published=published,
            baseline=baseline,
            variant_v3=variant_v3,
            model=model,
        )

    brief = await v5._generate_json_without_response_format(
        model=model,
        timeout=90.0,
        messages=v4.build_semantic_brief_messages(
            lane=lane,
            card_id=card_id,
            published=published,
            baseline=baseline,
            variant_v3=variant_v3,
        ),
        client_factory=lambda selected_model, selected_timeout: v1.build_card_content_client(
            selected_model,
            timeout=selected_timeout,
        ),
        max_tokens=4096,
    )
    if not brief:
        raise ValueError("semantic brief is empty")
    return brief


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
            return await generate_semantic_brief_once(
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
    writer_messages = build_v9_writer_messages(writer_base_messages, semantic_brief=semantic_brief)
    writer_messages = v7.build_concise_writer_messages(writer_messages)
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
    issues = v7.find_v7_copy_issues(variant)
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
        variant = await v7.repair_v7_copy_fields(
            variant,
            semantic_brief=semantic_brief,
            issues=issues,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
            response_schema=schema,
        )
        issues = v7.find_v7_copy_issues(variant)
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
        raise ValueError("v9 copy issues remain: " + "; ".join(issues[:8]))
    return baseline, variant, semantic_brief


def render_v9_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v7.render_v7_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v9 deepseekflash-mimo25 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v9_deepseekflash_mimo25_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v9_deepseekflash_mimo25_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v9_markdown_report(rows), encoding="utf-8")
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
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v9 deepseekflash-mimo25")
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
