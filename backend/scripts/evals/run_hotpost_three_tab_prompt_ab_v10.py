"""Three-tab Hotpost prompt A/B v10 Reddit-context semantic comparison.

V9 is the baseline. V10 keeps the same DeepSeek Flash -> MiMo v2.5 Pro model
chain, but asks the semantic layer to translate Reddit jargon, sarcasm, memes,
and community context before the Chinese writer sees the brief. Production
prompts are untouched.
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
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v9 as v9
from app.services.llm.interfaces import LLMClientError


REPORTS_EVALS_DIR = v9.REPORTS_EVALS_DIR
SEMANTIC_MODEL = v9.SEMANTIC_MODEL
WRITER_MODEL = v9.WRITER_MODEL
BASELINE_MODEL = v9.BASELINE_MODEL
V9_RESULTS_PATH = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v9_deepseekflash_mimo25_results.json"


def build_v10_semantic_brief_messages(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
) -> list[dict[str, str]]:
    messages = v4.build_semantic_brief_messages(
        lane=lane,
        card_id=card_id,
        published=published,
        baseline=baseline,
        variant_v3=variant_v3,
    )
    reddit_context_instruction = """

## V10 Reddit context translation

The final reader is a Chinese product user who may not understand Reddit,
developer slang, ad-tech terms, AI-agent hype, memes, or sarcasm.

Add these JSON keys to the semantic brief:
- reddit_context_translation: translate what the Reddit thread is really saying in everyday Chinese.
- jargon_or_meme_explainer: explain any Reddit/developer/AI slang, meme, quote, acronym, or implied background that would confuse a normal Chinese reader.
- sarcasm_or_tone: state whether the thread is sincere, sarcastic, self-mocking, angry, skeptical, or joking; explain the practical meaning, not the joke.
- plain_chinese_angle: tell the Chinese writer the simplest angle that makes the card understandable without opening the detail page.
- literal_translation_traps: list words or phrases that must not be translated literally because the meaning depends on Reddit context.

Interpretation rules:
- Do not translate literally when Reddit wording is sarcastic, meme-like, or shorthand.
- Separate facts from attitude: what happened, what commenters believe, and what they are mocking.
- If a comment is only one person's opinion, do not turn it into community consensus.
- Preserve evidence boundaries; do not inflate jokes, complaints, or demo claims into proven market facts.
- Prefer one clear Chinese explanation over a clever title-style phrase.
""".rstrip()
    return [{**messages[0], "content": messages[0]["content"] + reddit_context_instruction}, *messages[1:]]


def load_v9_baseline_rows(path: Path = V9_RESULTS_PATH) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("v9 results must be a list")
    by_card_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        card_id = str(row.get("card_id") or "")
        if card_id:
            by_card_id[card_id] = row
    return by_card_id


async def generate_v10_semantic_brief_once(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    brief = await v5._generate_json_without_response_format(
        model=model,
        timeout=90.0,
        messages=build_v10_semantic_brief_messages(
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


async def generate_v10_semantic_brief_with_retry(
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
            return await generate_v10_semantic_brief_once(
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


async def _generate_fields_with_brief(
    draft: v1.ValidationCardDraft | v1.WritingCardDraft,
    *,
    rules: dict[str, Any],
    banned: list[str],
    writer_model: str,
    semantic_brief: dict[str, Any],
    lane: str,
    card_id: str,
) -> dict[str, Any]:
    writer_base_messages = v1._with_overlay(
        v1._messages_for_draft(draft, rules=rules, banned=banned),
        enabled=True,
    )
    model, timeout, max_tokens, schema = v1._model_route_for_draft(
        draft,
        rules=rules,
        models=v1.load_card_content_models(),
        model_override=writer_model,
    )
    writer_messages = v9.build_v9_writer_messages(writer_base_messages, semantic_brief=semantic_brief)
    writer_messages = v7.build_concise_writer_messages(writer_messages)
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
    if issues:
        raise ValueError("v10 copy issues remain: " + "; ".join(issues[:8]))
    return variant


def render_v10_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v7.render_v7_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v10 reddit-context 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v10_reddit_context_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v10_reddit_context_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v10_markdown_report(rows), encoding="utf-8")
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
        banned = v1._all_banned_patterns(rules)
        v9_rows = load_v9_baseline_rows()
        rows: list[dict[str, Any]] = []
        model_label = "v9 baseline vs v10 reddit-context"
        for lane in v1.LANE_ORDER:
            for card in samples[lane]:
                draft = v1.card_to_draft(card)
                baseline: dict[str, Any] = {}
                variant: dict[str, Any] = {}
                v9_brief: dict[str, Any] = {}
                v10_brief: dict[str, Any] = {}
                variant_error = ""
                try:
                    card_id = str(card["card_id"])
                    v9_row = v9_rows.get(card_id)
                    if not v9_row:
                        raise ValueError(f"missing v9 baseline row for {card_id}")
                    baseline = v9_row.get("variant") or {}
                    v9_brief = v9_row.get("semantic_brief") or {}
                    source_baseline = v9_row.get("baseline") or baseline
                    print(
                        json.dumps(
                            {"event": "phase", "phase": "v10_semantic_start", "lane": lane, "card_id": card_id},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    v10_brief = await generate_v10_semantic_brief_with_retry(
                        lane=lane,
                        card_id=card_id,
                        published=v1._published_fields(card),
                        baseline=source_baseline,
                        variant_v3=source_baseline,
                        model=semantic_model,
                    )
                    print(
                        json.dumps(
                            {"event": "phase", "phase": "v10_writer_start", "lane": lane, "card_id": card_id},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    variant = await _generate_fields_with_brief(
                        draft,
                        rules=rules,
                        banned=banned,
                        writer_model=writer_model,
                        semantic_brief=v10_brief,
                        lane=lane,
                        card_id=card_id,
                    )
                except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
                    variant_error = f"{type(exc).__name__}: {exc}"
                rows.append(
                    {
                        "lane": lane,
                        "card_id": card["card_id"],
                        "model": model_label,
                        "published": v1._published_fields(card),
                        "baseline_semantic_brief": v9_brief,
                        "semantic_brief": v10_brief,
                        "baseline": baseline,
                        "variant": variant,
                        "baseline_error": "",
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
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v10 reddit-context")
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
