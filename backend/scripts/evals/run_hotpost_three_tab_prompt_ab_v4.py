"""Three-tab Hotpost prompt A/B v4 two-stage comparison.

Gemini reads the English Reddit evidence and produces a structured semantic
brief. Qwen then uses that brief to generate the final Chinese card fields.
This is a read-only experiment runner; production prompts are untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v3 as v3

from app.services.hotpost.card_content_llm_router import build_card_content_client
from app.services.llm.clients.gemini_client import GeminiChatClient


REPORTS_EVALS_DIR = v1.REPORTS_EVALS_DIR
LANE_ORDER = v1.LANE_ORDER
SEMANTIC_MODEL = "google/gemini-3.1-pro-preview"
WRITER_MODEL = "qwen/qwen3.6-max-preview"
BASELINE_MODEL = "deepseek/deepseek-v4-pro"


def _strip_google_prefix(model: str) -> str:
    return model.split("/", 1)[1] if model.startswith("google/") else model


def build_semantic_brief_messages(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
) -> list[dict[str, str]]:
    system = """
You are the semantic interpretation layer for a Reddit signal card.

Read the English Reddit evidence and the current Chinese card drafts. Do not
write the final Chinese card. Produce a compact JSON semantic brief that a
separate Chinese editor can use.

Required JSON keys:
- core_interpretation: what the English Reddit evidence really means.
- evidence_boundary: what the evidence does not prove and must not be inflated into.
- user_tension: who is under pressure and what tradeoff they are facing.
- why_it_matters_now: why this evidence changes the evaluation now.
- chinese_writing_guidance: how to explain it in plain Chinese without report tone.
- field_guidance: object with guidance for title, summary_line, why_now, why_test_now, and detail fields.

Constraints:
- Use English reasoning internally, but output the JSON values in Chinese.
- Preserve facts. Do not add outside background.
- Be deeper than a summary: explain pressure, tradeoff, and judgment boundary.
- Do not write the final Chinese card.
""".strip()
    user = {
        "lane": lane,
        "card_id": card_id,
        "published_card": published,
        "single_stage_baseline": baseline,
        "v3_variant_reference": variant_v3,
        "task": "Interpret the English Reddit evidence behind this card for a Chinese card writer.",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
    ]


def build_writer_messages(
    messages: list[dict[str, str]],
    *,
    semantic_brief: dict[str, Any],
) -> list[dict[str, str]]:
    brief_text = json.dumps(semantic_brief, ensure_ascii=False, indent=2)
    instruction = f"""

## Gemini semantic brief

下面是 Gemini 对英文 Reddit 证据的语义理解。你是中文字段编辑，只基于这个 brief 和原始输入生成中文字段。

{brief_text}

写作要求：
- 保持原 JSON 字段和结构不变。
- 中文字段要顺，按语义加标点，让用户能一眼读懂。
- 不要照抄 brief，要把它转成自然中文卡片。
- 不新增事实；brief 说不能夸大的地方，一律收窄。
""".rstrip()
    return [{**messages[0], "content": messages[0]["content"] + instruction}, *messages[1:]]


def with_v4_banned_patterns(rules: dict[str, Any]) -> dict[str, Any]:
    return v3.with_v3_banned_patterns(copy.deepcopy(rules))


def _safe_json_object(payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else {}
    except Exception:
        start = payload.find("{")
        end = payload.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(payload[start : end + 1])
            return data if isinstance(data, dict) else {}
    return {}


async def generate_semantic_brief(
    *,
    lane: str,
    card_id: str,
    published: dict[str, Any],
    baseline: dict[str, Any],
    variant_v3: dict[str, Any],
    model: str = SEMANTIC_MODEL,
) -> dict[str, Any]:
    client = GeminiChatClient(model=_strip_google_prefix(model), timeout=60.0)
    content = await client.generate(
        build_semantic_brief_messages(
            lane=lane,
            card_id=card_id,
            published=published,
            baseline=baseline,
            variant_v3=variant_v3,
        ),
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=4096,
    )
    brief = _safe_json_object(content)
    if not brief:
        raise ValueError("semantic brief is empty")
    return brief


async def _generate_fields_from_messages(
    draft: v1.ValidationCardDraft | v1.WritingCardDraft,
    *,
    rules: dict[str, Any],
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    response_schema: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    async def _attempt(attempt_messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = await v1._generate_json(
            model=model,
            timeout=timeout,
            messages=attempt_messages,
            client_factory=lambda selected_model, selected_timeout: build_card_content_client(
                selected_model,
                timeout=selected_timeout,
            ),
            max_tokens=max_tokens,
            response_schema=response_schema,
        )
        if isinstance(draft, v1.WritingCardDraft) or draft.lane == "breakdown":
            generated = v1._apply_breakdown_content(draft, payload, rules)
        else:
            generated = v1._apply_validation_content(draft, payload, rules)
            generated = v1.finalize_validation_readout(generated, source_draft=draft, rules=rules)
        return v1.extract_fields(generated)

    attempt_messages = messages
    last_error: ValueError | None = None
    for _ in range(3):
        try:
            return await _attempt(attempt_messages)
        except ValueError as exc:
            if not v1._should_retry_generation_error(exc):
                raise
            last_error = exc
            attempt_messages = v1._with_retry_instruction(attempt_messages, exc)
    raise last_error or ValueError("generation failed")


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
    baseline, _ = await v1.generate_one(
        draft,
        rules=rules,
        models=models,
        banned=banned,
        variant=True,
        model_override=baseline_model,
    )
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
    semantic_brief = await generate_semantic_brief(
        lane=str(card.get("lane") or ""),
        card_id=str(card.get("card_id") or ""),
        published=published,
        baseline=baseline,
        variant_v3=baseline,
        model=semantic_model,
    )
    writer_messages = build_writer_messages(writer_base_messages, semantic_brief=semantic_brief)
    variant = await _generate_fields_from_messages(
        draft,
        rules=rules,
        messages=writer_messages,
        model=model,
        max_tokens=max_tokens,
        response_schema=schema,
        timeout=timeout,
    )
    return baseline, variant, semantic_brief


def render_v4_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v1.render_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v4 two-stage 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v4_two_stage_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v4_two_stage_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v4_markdown_report(rows), encoding="utf-8")
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
        rules = with_v4_banned_patterns(v1.load_card_content_rules())
        models = v1.load_card_content_models()
        banned = v1._all_banned_patterns(rules)
        rows: list[dict[str, Any]] = []
        model_label = f"{semantic_model} -> {writer_model}"
        for lane in LANE_ORDER:
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
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v4 two-stage")
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
